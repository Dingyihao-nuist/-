---
name: unit-test
description: 为 Python (pytest) 和 JavaScript (vitest) 代码生成并运行单元测试。覆盖模型、服务、工具函数、API 路由，mock 外部依赖。
---

# 单元测试生成与执行器

为目标模块生成完善的单元测试并执行。Python 项目默认使用 pytest + pytest-asyncio，前端默认使用 vitest。

## 工作流程

1. **分析**目标模块 — 识别可测试单元（纯函数、服务类、API 路由、数据模型、工具函数）
2. **编写**测试文件，放到 `tests/` 目录下，遵循项目已有的测试模式
3. **运行**测试，使用 `-v` 显示详细输出，`--tb=short` 精简错误信息
4. **报告**结果 — 通过/失败数量、失败原因摘要、修复建议

## 测试设计原则

- **Mock 所有外部依赖**：数据库会话（AsyncMock）、HTTP 客户端、LLM API、文件读写、向量存储
- **使用 fixtures**：在 `conftest.py` 中创建可复用的 pytest fixtures，如 DB 会话、测试客户端、认证 Token
- **先覆盖正常路径**，再覆盖边界场景（空输入、无效数据、认证失败、超时、重复操作）
- **API 测试**：使用 `httpx.AsyncClient` + `ASGITransport` 进行异步 FastAPI 集成测试
- **隔离性**：每个测试独立创建数据、独立清理，不依赖执行顺序
- **命名规范**：文件用 `test_{模块名}.py`，函数用 `test_{被测函数}_{场景描述}`

## 测试清单（必须覆盖）

对每个模块回答以下问题并编写对应用例：

| 场景类型 | 示例 | 预期行为 |
|----------|------|----------|
| **正常路径** | 正确用户名+密码登录 | 返回 200 + Token |
| **参数无效** | 缺少必填字段 / 格式错误 | 返回 422 |
| **数据不存在** | 查询不存在的用户/文档 | 返回 404 |
| **重复操作** | 注册已存在的用户名 | 返回 409 |
| **权限不足** | 普通用户访问 Admin 接口 | 返回 403 |
| **认证失败** | 无 Token / Token 过期 / 错误密码 | 返回 401 |
| **空输入** | 空字符串 / None / 空列表 | 安全处理，不崩溃 |
| **并发/边界** | 超长输入 / 分页边界 / 大量数据 | 正确处理 |

## Python (pytest) 模板

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

# ---------- fixtures ----------
@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    return session

# ---------- 服务层测试 ----------
@pytest.mark.asyncio
async def test_register_success(mock_db):
    """正常注册 → 返回用户对象"""
    from app.services.auth_service import register_user

    user = await register_user(mock_db, "newuser", "new@test.com", "pass123")
    assert user.username == "newuser"
    mock_db.add.assert_called_once()

@pytest.mark.asyncio
async def test_register_duplicate(mock_db):
    """重复用户名 → HTTPException 409"""
    import pytest
    from fastapi import HTTPException
    from app.services.auth_service import register_user

    mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await register_user(mock_db, "exist", "e@t.com", "pass")
    assert exc.value.status_code == 409

# ---------- API 集成测试 ----------
@pytest.mark.asyncio
async def test_login_ok(mock_db):
    """正确凭据 → 200 + Token"""
    from app.main import app
    from app.utils.security import hash_password

    user = MagicMock()
    user.id = 1; user.username = "admin"; user.role = "admin"
    user.is_active = True
    user.password_hash = hash_password("123456")
    mock_db.execute.return_value.scalar_one_or_none.return_value = user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
    assert resp.status_code == 200
    assert "access_token" in resp.json()
```

## JavaScript (vitest) 模板

```js
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '../stores/useAuthStore';

describe('useAuthStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.setState({ user: null, isAuthenticated: false });
  });

  it('登录成功后更新状态', () => {
    const store = useAuthStore.getState();
    store.login('token-xxx', 'refresh-xxx', { id: 1, username: 'admin', role: 'admin' });

    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().isAdmin).toBe(true);
    expect(localStorage.getItem('access_token')).toBe('token-xxx');
  });

  it('退出登录清空状态和本地存储', () => {
    const store = useAuthStore.getState();
    store.login('token-xxx', 'refresh-xxx', { id: 1, username: 'admin' });
    store.logout();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
  });
});
```

## 执行命令

```bash
# Python — 全部测试
cd backend && source venv/Scripts/activate && python -m pytest tests/ -v --tb=short

# Python — 单个文件
python -m pytest tests/test_security.py -v

# Python — 单个测试函数
python -m pytest tests/test_security.py::TestPasswordHashing::test_hash_returns_string -v

# JavaScript
cd frontend && npx vitest run
```
