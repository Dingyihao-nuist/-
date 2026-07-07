"""文档处理流水线：加载 → 分块 → 向量化 → 存入 ChromaDB"""

import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, CSVLoader,
    Docx2txtLoader, UnstructuredMarkdownLoader,
    UnstructuredExcelLoader,
)
from langchain_core.documents import Document as LCDocument
from app.config import settings
from app.rag.vectorstore import get_vector_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 文件类型 → Loader 映射
LOADER_MAP = {
    "pdf": PyPDFLoader,
    "txt": TextLoader,
    "csv": CSVLoader,
    "docx": Docx2txtLoader,
    "md": UnstructuredMarkdownLoader,
    "xlsx": UnstructuredExcelLoader,
}


def get_file_type(extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if ext in LOADER_MAP:
        return ext
    raise ValueError(f"不支持的文件格式: {ext}")


def _read_txt_safe(file_path: str) -> str:
    """安全读取 TXT 文件，依次尝试常见中文编码"""
    encodings = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 最后兜底
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


async def ingest_file(file_path: str, filename: str) -> int:
    """
    处理单个文档：加载 → 分块 → 向量化 → 存入 ChromaDB
    返回分块数量
    """
    file_ext = get_file_type(os.path.splitext(filename)[1])
    logger.info(f"开始处理文档: {filename} (类型: {file_ext})")

    # 1. 加载文档
    docs = []
    if file_ext == "txt":
        # 手动处理 TXT 编码问题
        text = _read_txt_safe(file_path)
        if not text.strip():
            raise ValueError("文档内容为空")
        docs = [LCDocument(page_content=text, metadata={"source": filename})]
    elif file_ext == "csv":
        # CSV 也需要处理编码
        text = _read_txt_safe(file_path)
        if not text.strip():
            raise ValueError("文档内容为空")
        docs = [LCDocument(page_content=text, metadata={"source": filename})]
    else:
        loader_class = LOADER_MAP[file_ext]
        loader = loader_class(file_path)
        docs = loader.load()

    if not docs:
        raise ValueError("文档内容为空")

    # 2. 智能分块
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "；", ".", " ", ""],
    )
    chunks = text_splitter.split_documents(docs)

    # 3. 添加元数据
    for i, chunk in enumerate(chunks):
        chunk.metadata["filename"] = filename
        chunk.metadata["chunk_index"] = i
        chunk.metadata["file_type"] = file_ext

    # 4. 向量化 & 存入 ChromaDB
    vector_store = get_vector_store()
    vector_store.add_documents(chunks)
    logger.info(f"文档 {filename} 处理完成，共 {len(chunks)} 个分块")

    return len(chunks)


async def delete_from_vectorstore(doc_filename: str):
    """根据文档名从 ChromaDB 删除向量"""
    vector_store = get_vector_store()
    try:
        # ChromaDB 通过 metadata 过滤删除
        results = vector_store.get(where={"filename": doc_filename})
        ids = results.get("ids", [])
        if ids:
            vector_store.delete(ids=ids)
    except Exception as e:
        # 删除向量失败时不阻塞主流程，但记录日志便于排查
        logger.warning(f"从向量存储删除文档 {doc_filename} 失败: {e}")
