"""测试认证 API 端点 (FastAPI TestClient)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def mock_db_session():
    """Mock DB session for all API tests"""
    with patch("app.database.session.AsyncSessionLocal") as mock:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        mock.return_value.__aenter__.return_value = session
        yield session


@pytest.fixture
def mock_seed():
    """跳过 seed_admin"""
    with patch("app.main.seed_admin", new_callable=AsyncMock):
        yield


@pytest.fixture
def mock_chroma():
    """跳过 ChromaDB / Embedding 初始化（延迟加载，启动时不需要）"""
    yield


class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_register_success(self, mock_db_session, mock_seed, mock_chroma):
        """注册成功 → 201"""
        # Mock: 数据库查询返回 None (用户不存在)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/auth/register", json={
                "username": "newuser",
                "email": "new@test.com",
                "password": "password123",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"] == "注册成功"
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate(self, mock_db_session, mock_seed, mock_chroma):
        """注册重复用户 → 409"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # 用户已存在
        mock_db_session.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/auth/register", json={
                "username": "duplicate",
                "email": "dup@test.com",
                "password": "password123",
            })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, mock_db_session, mock_seed, mock_chroma):
        """缺少必填字段 → 422"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/auth/register", json={
                "username": "incomplete",
            })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, mock_db_session, mock_seed, mock_chroma):
        """登录成功 → 200"""
        from app.utils.security import hash_password

        user = MagicMock()
        user.id = 1
        user.username = "admin"
        user.email = "admin@test.com"
        user.role = "admin"
        user.is_active = True
        user.password_hash = hash_password("123456")
        user.created_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/auth/login", json={
                "username": "admin",
                "password": "123456",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "admin"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, mock_db_session, mock_seed, mock_chroma):
        """密码错误 → 401"""
        from app.utils.security import hash_password

        user = MagicMock()
        user.is_active = True
        user.password_hash = hash_password("123456")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/auth/login", json={
                "username": "admin",
                "password": "wrong",
            })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_health_check(self, mock_seed, mock_chroma):
        """健康检查 → 200"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_me_without_token(self, mock_seed, mock_chroma):
        """未认证访问 → 401"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, mock_seed, mock_chroma):
        """无效刷新令牌 → 401"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/auth/refresh", json={
                "refresh_token": "invalid.token.here",
            })
        assert resp.status_code == 401
