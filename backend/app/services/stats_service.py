"""统计数据聚合服务"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.session import Session
from app.models.message import Message


async def get_overview(db: AsyncSession) -> dict:
    """总览统计"""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_sessions = (await db.execute(select(func.count(Session.id)))).scalar() or 0
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0

    # 好评率
    total_feedback = (await db.execute(
        select(func.count(Message.id)).where(Message.feedback.isnot(None))
    )).scalar() or 0
    positive = (await db.execute(
        select(func.count(Message.id)).where(Message.feedback == True)
    )).scalar() or 0
    feedback_rate = f"{(positive / total_feedback * 100):.1f}%" if total_feedback > 0 else "N/A"

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "feedback_rate": feedback_rate,
    }


async def get_popular_questions(db: AsyncSession, limit: int = 10) -> dict:
    """热门问题 Top N"""
    result = await db.execute(
        select(Message.content, func.count(Message.id).label("count"))
        .where(Message.role == "user")
        .group_by(Message.content)
        .order_by(func.count(Message.id).desc())
        .limit(limit)
    )
    questions = [{"question": row[0][:60], "count": row[1]} for row in result.all()]

    return {"questions": questions}
