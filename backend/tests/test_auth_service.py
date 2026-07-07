"""测试认证业务逻辑 (mocked DB)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.services.auth_service import register_user, login_user, change_password, refresh_access_token
from app.utils.security import hash_password, create_access_token, create_refresh_token


class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_register_success(self, mock_db):
        """正常注册新用户"""
        # Arrange: 模拟数据库查询返回空（用户名和邮箱都不存在）
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        user = await register_user(mock_db, "newuser", "new@test.com", "password123")

        # Assert
        assert user.username == "newuser"
        assert user.email == "new@test.com"
        assert user.role == "user"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, mock_db):
        """注册重复用户名应抛出 409"""
        existing_user = MagicMock()
        existing_user.username = "existing"

        async def mock_execute(stmt):
            result = MagicMock()
            # 简单模拟: 假设任何查询都返回已存在的用户
            result.scalar_one_or_none.return_value = existing_user
            return result

        mock_db.execute = mock_execute

        with pytest.raises(HTTPException) as exc:
            await register_user(mock_db, "existing", "new@test.com", "password123")
        assert exc.value.status_code == 409
        assert "用户名已存在" in exc.value.detail

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, mock_db):
        """注册重复邮箱应抛出 409"""
        call_count = [0]

        async def mock_execute(stmt):
            result = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                # username check → no duplicate
                result.scalar_one_or_none.return_value = None
            else:
                # email check → existing user found
                result.scalar_one_or_none.return_value = MagicMock()
            return result

        mock_db.execute = mock_execute

        with pytest.raises(HTTPException) as exc:
            await register_user(mock_db, "newuser", "exist@test.com", "password123")
        assert exc.value.status_code == 409


class TestLoginUser:
    @pytest.mark.asyncio
    async def test_login_success(self, mock_db):
        """正确凭据登录成功"""
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
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await login_user(mock_db, "admin", "123456")

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["username"] == "admin"
        assert result["user"]["role"] == "admin"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, mock_db):
        """错误密码登录失败"""
        user = MagicMock()
        user.password_hash = hash_password("123456")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await login_user(mock_db, "admin", "wrongpassword")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, mock_db):
        """用户不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await login_user(mock_db, "nonexistent", "123456")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, mock_db):
        """已禁用用户登录失败"""
        user = MagicMock()
        user.is_active = False
        user.password_hash = hash_password("123456")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await login_user(mock_db, "admin", "123456")
        assert exc.value.status_code == 401


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_change_password_success(self, mock_db):
        user = MagicMock()
        user.password_hash = hash_password("oldpassword")

        await change_password(mock_db, user, "oldpassword", "newpassword")

        assert user.password_hash != hash_password("oldpassword")  # hash 更新了
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, mock_db):
        user = MagicMock()
        user.password_hash = hash_password("correct_old")

        with pytest.raises(HTTPException) as exc:
            await change_password(mock_db, user, "wrong_old", "newpassword")
        assert exc.value.status_code == 400
        assert "当前密码不正确" in exc.value.detail


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_success(self):
        refresh = create_refresh_token({"sub": "1", "username": "admin", "role": "admin"})
        result = await refresh_access_token(refresh)

        assert "access_token" in result
        assert "refresh_token" in result

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self):
        """用 access token 来 refresh 应该失败"""
        access = create_access_token({"sub": "1"})

        with pytest.raises(HTTPException) as exc:
            await refresh_access_token(access)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self):
        with pytest.raises(HTTPException) as exc:
            await refresh_access_token("invalid.token.here")
        assert exc.value.status_code == 401
