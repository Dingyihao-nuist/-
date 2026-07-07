"""LangChain RAG Chain 编排：记忆 + 检索 + 生成"""

import asyncio
from typing import AsyncIterator
from collections import OrderedDict
from app.rag.retriever import retrieve
from app.rag.generator import stream_generate
from app.utils.logger import get_logger

logger = get_logger(__name__)

# LRU 检索结果缓存（注意：OrderedDict 非线程安全，高并发场景下需替换为 aiocache 或 Redis）
_cache = OrderedDict()
_cache_lock = asyncio.Lock()
MAX_CACHE_SIZE = 256
HISTORY_MESSAGE_LIMIT = 6  # 历史消息保留数量


def _cache_key(query: str) -> str:
    return query.strip().lower()


async def _cached_retrieve(query: str):
    """带异步锁的 LRU 缓存检索，避免并发请求下缓存竞态条件"""
    key = _cache_key(query)
    async with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)  # LRU：最近访问的移到末尾
            return _cache[key]

    docs, sources = await retrieve(query)

    async with _cache_lock:
        _cache[key] = (docs, sources)
        _cache.move_to_end(key)
        if len(_cache) > MAX_CACHE_SIZE:
            _cache.popitem(last=False)  # 删除最旧条目

    return docs, sources


async def rag_query(
    question: str,
    chat_history_messages: list = None,
    use_cache: bool = True,
) -> AsyncIterator[dict]:
    """
    RAG 查询主流程：
    1. 检索相关文档
    2. 流式生成回答
    3. 在生成结束后返回来源引用
    """
    if chat_history_messages is None:
        chat_history_messages = []

    # 1. 检索
    try:
        if use_cache:
            docs, sources = await _cached_retrieve(question)
        else:
            docs, sources = await retrieve(question)
    except Exception as e:
        logger.error(f"检索失败: {e}", exc_info=True)
        yield {"type": "error", "message": "检索服务暂时不可用，请稍后重试"}
        return

    # 2. 流式生成（无论有没有文档都调用 LLM）
    # 有文档 → RAG prompt；无文档 → 通用 prompt，千问直接回答
    sources_yielded = False
    async for event in stream_generate(question, docs, chat_history_messages):
        yield event
        # 第一个 token 之后立即发送 sources
        if event["type"] == "token" and not sources_yielded:
            yield {"type": "sources", "sources": sources}
            sources_yielded = True

    if not sources_yielded:
        yield {"type": "sources", "sources": sources}


def clear_retrieval_cache():
    """清空检索缓存（知识库更新后调用）"""
    _cache.clear()
