"""ChromaDB 向量存储客户端管理"""

import os
import shutil
from langchain_chroma import Chroma
from app.config import settings
from app.rag.embeddings import get_embeddings

_vector_store = None


def get_vector_store() -> Chroma:
    """获取全局 ChromaDB 客户端"""
    global _vector_store
    if _vector_store is None:
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        _vector_store = Chroma(
            collection_name="kb_chunks",
            embedding_function=get_embeddings(),
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
    return _vector_store


def reset_vector_store():
    """重建向量存储（清空所有数据）"""
    global _vector_store
    persist_dir = settings.CHROMA_PERSIST_DIR
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        os.makedirs(persist_dir, exist_ok=True)
    _vector_store = None
    return get_vector_store()
