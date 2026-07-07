"""pytest fixtures — shared test infrastructure"""

import os
import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# 确保 backend 在 Python path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session")
def event_loop():
    """为整个 test session 创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy async session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """返回一个模拟的普通用户对象"""
    user = MagicMock()
    user.id = 2
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "user"
    user.is_active = True
    user.created_at = None
    return user


@pytest.fixture
def mock_admin():
    """返回一个模拟的管理员用户对象"""
    admin = MagicMock()
    admin.id = 1
    admin.username = "admin"
    admin.email = "admin@example.com"
    admin.role = "admin"
    admin.is_active = True
    admin.created_at = None
    return admin


@pytest.fixture
def mock_user_model():
    """Mock User SQLAlchemy model — 返回 MagicMock 实例"""
    from unittest.mock import patch

    with patch("app.models.user.User") as mock:
        yield mock


@pytest.fixture
def test_settings():
    """覆盖配置用于测试"""
    from app.config import settings

    original_db = settings.DATABASE_URL
    settings.DATABASE_URL = "sqlite+aiosqlite:///./data/test_app.db"
    yield settings
    settings.DATABASE_URL = original_db
