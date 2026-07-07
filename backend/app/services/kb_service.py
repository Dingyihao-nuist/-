"""知识库管理业务逻辑"""

import os
import re
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile
from app.config import settings
from app.models.document import Document, Chunk
from app.models.user import User
from app.rag.ingestion import ingest_file, delete_from_vectorstore
from app.rag.chain import clear_retrieval_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def upload_document(db: AsyncSession, file: UploadFile, user: User) -> Document:
    """上传并处理文档"""
    # 验证文件大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    # 验证文件类型
    ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
    allowed = {"pdf", "docx", "txt", "md", "csv", "xlsx"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，支持: {', '.join(allowed)}")

    # 保存文件到磁盘（对文件名做安全处理，防止路径遍历攻击）
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', file.filename or "upload")
    safe_name = safe_name.lstrip('.') or "upload"  # 防止隐藏文件
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    doc = Document(
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        file_path=file_path,
        status="processing",
        uploaded_by=user.id,
    )
    db.add(doc)
    await db.flush()

    # 异步处理文档（分块+向量化）
    try:
        chunk_count = await ingest_file(file_path, file.filename)
        doc.chunk_count = chunk_count
        doc.status = "ready"

        # 创建 Chunk 记录（用于引用溯源）
        for i in range(chunk_count):
            chunk = Chunk(
                document_id=doc.id,
                chunk_index=i,
                content="",  # 实际内容在 ChromaDB 中
                chunk_metadata=f'{{"filename": "{file.filename}", "chunk_index": {i}}}',
            )
            db.add(chunk)

        # 清空检索缓存
        clear_retrieval_cache()

    except Exception as e:
        doc.status = "error"
        logger.error(f"文档处理失败 [{file.filename}]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="文档处理失败，请稍后重试")

    return doc


async def get_documents(db: AsyncSession, page: int = 1, per_page: int = 20, search: str = "") -> dict:
    """获取文档列表（分页）"""
    query = select(Document)

    if search:
        query = query.where(Document.filename.contains(search))

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    documents = result.scalars().all()

    return {
        "documents": documents,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def delete_document(db: AsyncSession, doc_id: int):
    """删除文档及关联数据"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 从 ChromaDB 删除向量
    await delete_from_vectorstore(doc.filename)

    # 删除磁盘文件
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # 从数据库删除
    await db.delete(doc)

    # 清空缓存
    clear_retrieval_cache()


async def get_document_chunks(db: AsyncSession, doc_id: int) -> list:
    """获取文档的分块列表"""
    result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
    )
    return result.scalars().all()


async def get_kb_stats(db: AsyncSession) -> dict:
    """获取知识库统计信息"""
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    chunk_count = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0
    size = (await db.execute(select(func.sum(Document.file_size)))).scalar() or 0

    return {
        "total_documents": doc_count,
        "total_chunks": chunk_count,
        "total_size": size,
    }
