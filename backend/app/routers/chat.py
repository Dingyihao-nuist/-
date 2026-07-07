"""聊天 & 问答路由 /api/chat/*"""

import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import CreateSessionRequest, RenameSessionRequest, QueryRequest, FeedbackRequest
from app.services.chat_service import (
    get_sessions, create_session, delete_session,
    rename_session, get_messages, stream_chat,
    update_feedback, export_session,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["问答"])


@router.get("/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户会话列表"""
    return await get_sessions(db, current_user, page)


@router.post("/sessions", status_code=201)
async def new_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新会话"""
    result = await create_session(db, current_user, req.title)
    await db.commit()
    return result


@router.put("/sessions/{session_id}")
async def edit_session(
    session_id: int,
    req: RenameSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重命名会话"""
    await rename_session(db, current_user, session_id, req.title)
    await db.commit()
    return {"message": "重命名成功"}


@router.delete("/sessions/{session_id}")
async def remove_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话"""
    await delete_session(db, current_user, session_id)
    await db.commit()
    return {"message": "会话已删除"}


@router.get("/sessions/{session_id}/messages")
async def session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话消息历史"""
    return await get_messages(db, current_user, session_id)


@router.post("/sessions/{session_id}/stream")
async def stream_query(
    session_id: int,
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """核心：SSE 流式问答"""
    async def event_generator():
        try:
            async for event_str in stream_chat(db, current_user, session_id, req.question):
                yield event_str
            await db.commit()
        except Exception as e:
            logger.error(f"SSE 流式对话异常 [session={session_id}]: {e}", exc_info=True)
            await db.rollback()
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': '服务暂时不可用，请稍后重试'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.put("/messages/{message_id}/feedback")
async def message_feedback(
    message_id: int,
    req: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """消息反馈（点赞/踩）"""
    await update_feedback(db, current_user, message_id, req.feedback)
    await db.commit()
    return {"message": "反馈成功"}


@router.get("/sessions/{session_id}/export")
async def export_chat(
    session_id: int,
    format: str = Query("md", pattern="^(md|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出对话"""
    content = await export_session(db, current_user, session_id, format)
    media_type = "text/markdown" if format == "md" else "application/pdf"
    filename = f"chat_export.{format}"

    from fastapi.responses import Response
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
