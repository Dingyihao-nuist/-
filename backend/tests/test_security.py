"""测试 JWT Token 和密码哈希工具函数"""

import pytest
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_returns_string(self):
        result = hash_password("mypassword")
        assert isinstance(result, str)
        assert len(result) > 0
        assert result.startswith("$2b$")  # bcrypt 格式

    def test_verify_correct_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_salts_produce_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # 盐值不同导致哈希不同

    def test_verify_both_hashes(self):
        h1 = hash_password("pwd")
        h2 = hash_password("pwd")
        assert verify_password("pwd", h1) is True
        assert verify_password("pwd", h2) is True

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_long_password(self):
        long_pwd = "a" * 50
        hashed = hash_password(long_pwd)
        assert verify_password(long_pwd, hashed) is True

    def test_unicode_password(self):
        pwd = "中文密码测试123!@#"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True


class TestJWTToken:
    def test_create_access_token_returns_string(self):
        token = create_access_token({"sub": "1", "username": "admin"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_refresh_token_returns_string(self):
        token = create_refresh_token({"sub": "1"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_valid_token(self):
        token = create_access_token({"sub": "1", "username": "admin", "role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "admin"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        result = decode_token("not.a.valid.token")
        assert result is None

    def test_decode_empty_token(self):
        result = decode_token("")
        assert result is None

    def test_decode_none_token(self):
        result = decode_token(None)
        assert result is None

    def test_access_and_refresh_have_different_types(self):
        access = create_access_token({"sub": "1"})
        refresh = create_refresh_token({"sub": "1"})

        access_payload = decode_token(access)
        refresh_payload = decode_token(refresh)

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_token_contains_expiry(self):
        from datetime import datetime, timezone
        token = create_access_token({"sub": "1"})
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Token 应该在 30 分钟内过期
        diff = (exp - now).total_seconds()
        assert 0 < diff < 1800  # 30 minutes
