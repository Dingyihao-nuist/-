"""会话 & 消息管理业务逻辑"""

import json
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.session import Session
from app.models.message import Message
from app.models.user import User
from app.rag.chain import rag_query, HISTORY_MESSAGE_LIMIT
from app.utils.logger import get_logger
from typing import AsyncIterator

logger = get_logger(__name__)
TITLE_TRUNCATE_LENGTH = 30  # 自动生成标题的最大长度


async def get_sessions(db: AsyncSession, user: User, page: int = 1, per_page: int = 50) -> dict:
    """获取用户会话列表"""
    query = (
        select(Session)
        .where(Session.user_id == user.id)
        .order_by(Session.updated_at.desc())
    )
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "user_id": s.user_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ],
        "total": total,
    }


async def create_session(db: AsyncSession, user: User, title: str = "新的聊天") -> dict:
    """创建新会话"""
    session = Session(user_id=user.id, title=title)
    db.add(session)
    await db.flush()
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


async def delete_session(db: AsyncSession, user: User, session_id: int):
    """删除会话"""
    session = await _verify_session_owner(db, user, session_id)
    await db.delete(session)


async def rename_session(db: AsyncSession, user: User, session_id: int, title: str):
    """重命名会话"""
    await db.execute(
        update(Session)
        .where(Session.id == session_id, Session.user_id == user.id)
        .values(title=title)
    )


async def _verify_session_owner(db: AsyncSession, user: User, session_id: int) -> Session:
    """验证会话属于当前用户，返回 Session 对象，否则抛出 404"""
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


async def get_messages(db: AsyncSession, user: User, session_id: int) -> dict:
    """获取会话消息历史"""
    session = await _verify_session_owner(db, user, session_id)

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return {
        "session": {
            "id": session.id,
            "title": session.title,
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "sources": m.sources,
                "feedback": m.feedback,
                "token_count": m.token_count,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


async def stream_chat(
    db: AsyncSession,
    user: User,
    session_id: int,
    question: str,
) -> AsyncIterator[str]:
    """流式问答处理"""
    session = await _verify_session_owner(db, user, session_id)

    # 获取历史消息（最近 N 条，N = HISTORY_MESSAGE_LIMIT）
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_MESSAGE_LIMIT)
    )
    history_messages = list(result.scalars().all())[::-1]  # 反转回正序

    # 保存用户消息并立即提交（释放写锁，避免 SSE 流期间长期持有）
    user_msg = Message(session_id=session_id, role="user", content=question)
    db.add(user_msg)
    await db.flush()

    # 自动生成会话标题（首次对话），处理纯空白字符边界情况
    if session.title == "新的聊天":
        trimmed = question.strip()
        if trimmed:
            session.title = trimmed[:TITLE_TRUNCATE_LENGTH] + ("..." if len(trimmed) > TITLE_TRUNCATE_LENGTH else "")
        else:
            session.title = "无标题对话"
        await db.flush()

    # 立即提交用户消息和标题，释放 SQLite 写锁
    # 后续 RAG 检索 + LLM 流式生成期间不再持有写锁
    await db.commit()

    # 收集完整回答和来源
    full_answer = ""
    sources = []

    # RAG 流式生成
    async for event in rag_query(question, history_messages):
        event_type = event.get("type")

        if event_type == "token":
            full_answer += event.get("content", "")
            yield f"event: token\ndata: {json.dumps({'type': 'token', 'content': event['content']})}\n\n"

        elif event_type == "sources":
            sources = event.get("sources", [])
            yield f"event: sources\ndata: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        elif event_type == "done":
            # 保存 AI 消息并立即提交
            ai_msg = Message(
                session_id=session_id,
                role="assistant",
                content=full_answer or event.get("content", ""),
                sources=json.dumps(sources, ensure_ascii=False),
            )
            db.add(ai_msg)
            await db.flush()

            # 更新会话时间
            from sqlalchemy import update as sql_update
            await db.execute(
                sql_update(Session)
                .where(Session.id == session_id)
                .values(updated_at=func.now())
            )

            # 提交 AI 消息，完成本次问答的全部数据库工作
            await db.commit()

            yield f"event: done\ndata: {json.dumps({'type': 'done', 'message_id': ai_msg.id})}\n\n"

        elif event_type == "error":
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': event['message']})}\n\n"


async def update_feedback(db: AsyncSession, user: User, message_id: int, feedback_value: bool):
    """更新消息反馈"""
    # 验证消息属于当前用户的会话
    result = await db.execute(
        select(Message).join(Session).where(
            Message.id == message_id,
            Session.user_id == user.id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")

    message.feedback = feedback_value
    await db.flush()


async def export_session(db: AsyncSession, user: User, session_id: int, fmt: str = "md") -> str:
    """导出会话为 Markdown 或 PDF"""
    session = await _verify_session_owner(db, user, session_id)

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    # 生成 Markdown
    lines = [
        f"# {session.title}",
        f"",
        f"导出时间: {func.now()}",
        f"---",
        f"",
    ]

    for m in messages:
        role_label = "**用户**" if m.role == "user" else "**AI 助手**"
        lines.append(f"### {role_label}")
        lines.append(m.content)
        lines.append("")
        if m.sources and m.role == "assistant":
            try:
                sources = json.loads(m.sources)
                if sources:
                    lines.append("*参考来源:*")
                    for i, s in enumerate(sources):
                        lines.append(f"- 来源{i+1}: {s.get('doc_name', '未知')}")
                    lines.append("")
            except (json.JSONDecodeError, TypeError) as e:
                # 来源数据格式异常时静默跳过，不影响导出主流程，但记录便于排查
                logger.debug(f"导出时跳过异常的 sources JSON [message_id={m.id}]: {e}")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
