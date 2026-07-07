"""LLM 生成器 — 阿里云百炼 DashScope (OpenAI 兼容模式)"""

from functools import lru_cache
from typing import AsyncIterator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 对话历史中每种消息保留数量 + 每条消息内容最大截断长度
HISTORY_MESSAGE_LIMIT = 6
CHAT_HISTORY_CONTENT_LIMIT = 200

# 有知识库上下文时的 System Prompt
RAG_SYSTEM_PROMPT = """你是专业的电商客服助手，由阿里云通义千问大模型驱动。请严格根据以下商品信息回答用户问题。

## 回答要求：
1. 使用 Markdown 格式输出
2. 在回答中使用 [来源N] 标注引用的信息来源
3. 如果涉及价格、库存等时效性信息，提醒用户以实际页面为准
4. 保持亲切专业的语气

## 商品参考信息：
{context}

## 历史对话：
{chat_history}"""

# 无知识库上下文时的 System Prompt（通用对话）
GENERAL_SYSTEM_PROMPT = """你是专业的电商客服助手，由阿里云通义千问大模型驱动。

由于知识库中暂无与用户问题直接相关的商品信息，请根据你自己的知识友好地回答用户问题。

## 回答要求：
1. 使用 Markdown 格式输出
2. 如果用户问的是通用问题（如"你是谁"、"你是什么模型"等），直接友好回答
3. 如果用户问的是具体商品问题但你无法确认，建议用户联系人工客服或查阅官方信息
4. 保持亲切专业的语气

## 历史对话：
{chat_history}"""


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """获取 LLM 实例（单例缓存）"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
        streaming=True,
    )


def build_context(docs: list) -> str:
    """构建 Prompt 上下文"""
    parts = []
    for i, doc in enumerate(docs, 1):
        filename = doc.metadata.get("filename", "未知文档")
        parts.append(f"[来源{i}] 文档: {filename}\n{doc.page_content}")
    return "\n\n".join(parts)


def build_chat_history(messages: list) -> str:
    """构建对话历史文本"""
    if not messages:
        return "（无历史对话）"
    recent = messages[-HISTORY_MESSAGE_LIMIT:]
    lines = []
    for msg in recent:
        role = "用户" if msg.role == "user" else "助手"
        lines.append(f"{role}: {msg.content[:CHAT_HISTORY_CONTENT_LIMIT]}")
    return "\n".join(lines)


async def stream_generate(
    question: str,
    docs: list,
    chat_history_messages: list,
) -> AsyncIterator[dict]:
    """
    流式生成回答
    - 有文档时：使用 RAG prompt（严格基于知识库）
    - 无文档时：使用通用 prompt（直接由千问回答）
    """
    llm = get_llm()
    history = build_chat_history(chat_history_messages)

    if docs:
        context = build_context(docs)
        system_content = RAG_SYSTEM_PROMPT.format(context=context, chat_history=history)
    else:
        system_content = GENERAL_SYSTEM_PROMPT.format(chat_history=history)

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=question),
    ]

    full_response = ""
    try:
        async for chunk in llm.astream(messages):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            if content:
                full_response += content
                yield {"type": "token", "content": content}
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}", exc_info=True)
        yield {"type": "error", "message": "LLM 服务暂时不可用，请稍后重试"}
        return

    yield {"type": "done", "content": full_response}
