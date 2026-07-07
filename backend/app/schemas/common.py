"""通用 Pydantic Schema"""

from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 20


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
