"""认证业务逻辑"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.user import User
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token


async def register_user(db: AsyncSession, username: str, email: str, password: str) -> User:
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="邮箱已被注册")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role="user",
    )
    db.add(user)
    await db.flush()
    return user


async def login_user(db: AsyncSession, username: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="账号已被禁用")

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


async def refresh_access_token(refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新令牌")

    token_data = {"sub": payload["sub"], "username": payload.get("username"), "role": payload.get("role")}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    return {"access_token": new_access, "refresh_token": new_refresh}


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str):
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")

    user.password_hash = hash_password(new_password)
    await db.flush()
