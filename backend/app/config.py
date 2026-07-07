"""应用配置管理 - 基于 pydantic-settings 从 .env 加载"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ============ 应用 ============
    APP_NAME: str = "EnterpriseRAG"
    DEBUG: bool = False
    SECRET_KEY: str = ""

    # ============ 阿里云百炼 DashScope ============
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen-plus"
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ============ Embedding ============
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"

    # ============ 数据库 ============
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # ============ ChromaDB ============
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # ============ JWT ============
    JWT_SECRET_KEY: str = ""
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ============ 文件上传 ============
    MAX_UPLOAD_SIZE_MB: int = 20
    UPLOAD_DIR: str = "./data/uploads"

    # ============ RAG 参数 ============
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_K: int = 20
    RERANK_TOP_K: int = 5
    RELEVANCE_THRESHOLD: float = 0.5
    LLM_TEMPERATURE: float = 0.1

    # ============ 限流 ============
    RATE_LIMIT: str = "20/minute"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 生产环境包装模式下强制校验 JWT 密钥强度
        if not self.DEBUG and len(self.JWT_SECRET_KEY) < 32:
            raise ValueError(
                "JWT_SECRET_KEY 必须至少 32 个字符，"
                "请通过环境变量或 .env 文件设置强密钥"
            )
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY 未设置，请通过环境变量或 .env 文件配置")


settings = Settings()
