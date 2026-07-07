"""认证路由 /api/auth/*"""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, RefreshRequest,
    ChangePasswordRequest, TokenResponse,
)
from app.services.auth_service import register_user, login_user, refresh_access_token, change_password

router = APIRouter(prefix="/api/auth", tags=["认证"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await register_user(db, req.username, req.email, req.password)
    return {"message": "注册成功", "user_id": user.id}


@router.post("/login")
@limiter.limit("10/minute")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    return await login_user(db, req.username, req.password)


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    return await refresh_access_token(req.refresh_token)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put("/change-password")
async def change_pwd(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await change_password(db, current_user, req.old_password, req.new_password)
    return {"message": "密码修改成功"}
