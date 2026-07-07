"""混合检索引擎：Dense(向量)+Sparse(BM25)→RRF融合→BGE-Reranker精排"""

from typing import List
from app.config import settings
from app.rag.vectorstore import get_vector_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Reranker 懒加载（可能因 PyTorch Windows 兼容性崩溃，优雅降级）
_reranker = None
_reranker_failed = False


def _try_load_reranker():
    """尝试加载 BGE-Reranker，失败则标记并降级为简单分数排序"""
    global _reranker, _reranker_failed
    if _reranker is not None:
        return _reranker
    if _reranker_failed:
        return None

    try:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("BAAI/bge-reranker-large", max_length=512)
        logger.info("Reranker loaded OK")
        return _reranker
    except Exception as e:
        logger.warning(f"Reranker 加载失败，降级为向量相似度排序: {e}")
        _reranker_failed = True
        return None


def _simple_rerank(documents: list, top_k: int = 5) -> list:
    """简单排序：按已有顺序取 top-k（无 reranker 时的降级方案）"""
    return documents[:top_k]


def _cross_encode_rerank(model, query: str, documents: list,
                         threshold: float, top_k: int) -> list:
    """Cross-Encoder 精排"""
    if not documents:
        return []

    pairs = [[query, doc.page_content] for doc in documents]
    scores = model.predict(pairs)
    scored = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
    filtered = [(doc, score) for doc, score in scored if score >= threshold]
    return [doc for doc, _ in filtered[:top_k]]


async def retrieve(query: str, k: int = 20) -> tuple[List, List]:
    """
    混合检索流程
    返回: (top_docs, source_metadatas)
    """
    vector_store = get_vector_store()

    # 1. 检查知识库是否为空
    try:
        all_data = vector_store.get()
        all_texts = all_data.get("documents", [])
    except Exception as e:
        logger.warning(f"读取向量存储失败，按空知识库处理: {e}")
        all_texts = []

    # 2. Dense 向量检索
    dense_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    # 3. 混合检索：BM25（如果有数据） + Dense
    if all_texts:
        try:
            from langchain_community.retrievers import BM25Retriever
            from langchain_classic.retrievers import EnsembleRetriever

            bm25_retriever = BM25Retriever.from_texts(
                all_texts,
                metadatas=all_data.get("metadatas", []),
            )
            bm25_retriever.k = k
            ensemble = EnsembleRetriever(
                retrievers=[dense_retriever, bm25_retriever],
                weights=[0.7, 0.3],
            )
            results = ensemble.invoke(query)
        except Exception as e:
            logger.warning(f"BM25 混合检索失败，降级为纯 Dense 检索: {e}")
            results = dense_retriever.invoke(query)
    else:
        # 知识库为空 → 直接返回空
        return [], []

    if not results:
        return [], []

    # 4. 精排：尝试 BGE-Reranker，失败则简单排序
    model = _try_load_reranker()
    if model:
        try:
            top_docs = _cross_encode_rerank(
                model, query, results,
                threshold=settings.RELEVANCE_THRESHOLD,
                top_k=settings.RERANK_TOP_K,
            )
        except Exception as e:
            logger.warning(f"Rerank 执行失败，降级: {e}")
            top_docs = _simple_rerank(results, settings.RERANK_TOP_K)
    else:
        top_docs = _simple_rerank(results, settings.RERANK_TOP_K)

    if not top_docs:
        return [], []

    # 5. 提取来源信息
    sources = []
    for doc in top_docs:
        sources.append({
            "doc_name": doc.metadata.get("filename", "未知文档"),
            "chunk_index": doc.metadata.get("chunk_index", 0),
            "preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
        })

    return top_docs, sources
