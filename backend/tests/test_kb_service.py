"""测试知识库管理业务逻辑"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.services.kb_service import get_kb_stats, get_documents


class TestKBStats:
    @pytest.mark.asyncio
    async def test_empty_stats(self, mock_db):
        """空知识库的统计数据"""
        async def mock_execute(stmt):
            result = MagicMock()
            result.scalar.return_value = 0
            return result
        mock_db.execute = mock_execute

        stats = await get_kb_stats(mock_db)
        assert stats["total_documents"] == 0
        assert stats["total_chunks"] == 0
        assert stats["total_size"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_data(self, mock_db):
        """有数据的知识库统计"""
        call_count = [0]

        async def mock_execute(stmt):
            result = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:  # document count
                result.scalar.return_value = 10
            elif idx == 1:  # chunk count
                result.scalar.return_value = 500
            else:  # total size
                result.scalar.return_value = 1024 * 1024 * 5
            return result

        mock_db.execute = mock_execute
        stats = await get_kb_stats(mock_db)

        assert stats["total_documents"] == 10
        assert stats["total_chunks"] == 500
        assert stats["total_size"] == 1024 * 1024 * 5


class TestGetDocuments:
    @pytest.mark.asyncio
    async def test_empty_list(self, mock_db):
        """空文档列表"""
        async def mock_execute(stmt):
            result = MagicMock()
            result.scalar.return_value = 0  # count
            result.scalars.return_value.all.return_value = []
            return result
        mock_db.execute = mock_execute

        result = await get_documents(mock_db, page=1, per_page=20)
        assert result["total"] == 0
        assert result["documents"] == []
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_with_search_filter(self, mock_db):
        """搜索过滤"""
        async def mock_execute(stmt):
            result = MagicMock()
            result.scalar.return_value = 0
            result.scalars.return_value.all.return_value = []
            return result
        mock_db.execute = mock_execute

        result = await get_documents(mock_db, page=1, per_page=20, search="商品")
        assert result["total"] == 0
        assert len(result["documents"]) == 0

    @pytest.mark.asyncio
    async def test_pagination(self, mock_db):
        """分页参数正确"""
        async def mock_execute(stmt):
            result = MagicMock()
            result.scalar.return_value = 25
            result.scalars.return_value.all.return_value = [MagicMock() for _ in range(10)]
            return result
        mock_db.execute = mock_execute

        result = await get_documents(mock_db, page=2, per_page=10)
        assert result["page"] == 2
        assert result["per_page"] == 10
        assert result["total"] == 25
        assert len(result["documents"]) == 10


class TestDeleteDocument:
    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_db):
        """删除不存在的文档 → 404"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.services.kb_service import delete_document
        with pytest.raises(HTTPException) as exc:
            await delete_document(mock_db, 999)
        assert exc.value.status_code == 404
        assert "文档不存在" in exc.value.detail
