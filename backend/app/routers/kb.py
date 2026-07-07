"""知识库管理路由 /api/kb/* (仅 Admin)"""

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services.kb_service import (
    upload_document, get_documents, delete_document,
    get_document_chunks, get_kb_stats,
)
from app.rag.ingestion import ingest_file, delete_from_vectorstore
from app.rag.chain import clear_retrieval_cache

router = APIRouter(prefix="/api/kb", tags=["知识库管理"])


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """上传文档（支持批量）"""
    results = []
    for file in files:
        doc = await upload_document(db, file, current_user)
        results.append({
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
        })
    await db.commit()
    return {"documents": results}


@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """文档列表（分页 + 搜索）"""
    return await get_documents(db, page, per_page, search)


@router.delete("/documents/{doc_id}")
async def delete_doc(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """删除文档及向量"""
    await delete_document(db, doc_id)
    await db.commit()
    return {"message": "文档已删除"}


@router.get("/documents/{doc_id}/chunks")
async def view_chunks(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """查看文档分块详情"""
    chunks = await get_document_chunks(db, doc_id)
    return {"chunks": chunks}


@router.post("/documents/{doc_id}/reindex")
async def reindex_doc(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """重建单个文档索引"""
    from sqlalchemy import select
    from app.models.document import Document
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 先删除旧向量
    await delete_from_vectorstore(doc.filename)
    clear_retrieval_cache()

    # 重新处理
    chunk_count = await ingest_file(doc.file_path, doc.filename)
    doc.chunk_count = chunk_count
    doc.status = "ready"
    await db.commit()

    return {"message": "重建完成", "chunk_count": chunk_count}


@router.get("/stats")
async def kb_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """知识库统计信息"""
    return await get_kb_stats(db)
