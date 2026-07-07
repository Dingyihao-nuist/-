"""测试配置管理"""

import pytest
from app.config import Settings


class TestSettings:
    def test_default_values(self):
        settings = Settings()
        assert settings.APP_NAME == "EnterpriseRAG"
        assert settings.LLM_MODEL == "qwen-plus"
        assert settings.LLM_TEMPERATURE == 0.1
        assert settings.CHUNK_SIZE == 500
        assert settings.CHUNK_OVERLAP == 50
        assert settings.RETRIEVAL_K == 20
        assert settings.RERANK_TOP_K == 5
        assert settings.RELEVANCE_THRESHOLD == 0.5
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.MAX_UPLOAD_SIZE_MB == 20
        assert settings.RATE_LIMIT == "20/minute"

    def test_embedding_model_default(self):
        settings = Settings()
        assert settings.EMBEDDING_MODEL == "BAAI/bge-m3"
        assert settings.EMBEDDING_DEVICE == "cpu"

    def test_llm_base_url(self):
        settings = Settings()
        assert "dashscope.aliyuncs.com" in settings.LLM_BASE_URL
        assert "compatible-mode" in settings.LLM_BASE_URL

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("CHUNK_SIZE", "800")
        monkeypatch.setenv("LLM_MODEL", "qwen-max")
        settings = Settings()
        assert settings.CHUNK_SIZE == 800
        assert settings.LLM_MODEL == "qwen-max"

    def test_boolean_parsing(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "false")
        settings = Settings()
        assert settings.DEBUG is False

    def test_float_parsing(self, monkeypatch):
        monkeypatch.setenv("LLM_TEMPERATURE", "0.3")
        settings = Settings()
        assert settings.LLM_TEMPERATURE == 0.3
