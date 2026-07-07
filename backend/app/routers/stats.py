"""统计路由 /api/stats/* (仅 Admin)"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services.stats_service import get_overview, get_popular_questions

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/overview")
async def overview(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """总览统计"""
    return await get_overview(db)


@router.get("/popular")
async def popular(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """热门问题"""
    return await get_popular_questions(db, limit)
