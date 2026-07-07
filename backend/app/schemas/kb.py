"""知识库管理 Pydantic Schema"""

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    created_at: str | None = None

    model_config = {"from_attributes": True}
