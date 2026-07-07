"""BGE-M3 嵌入模型管理（单例模式）"""

from langchain_huggingface import HuggingFaceEmbeddings
from app.config import settings

_embedding_model = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """获取全局唯一的 BGE-M3 嵌入模型实例"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": settings.EMBEDDING_DEVICE},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model
