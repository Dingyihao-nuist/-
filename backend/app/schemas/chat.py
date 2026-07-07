"""聊天相关 Pydantic Schema"""

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str = "新的聊天"


class RenameSessionRequest(BaseModel):
    title: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题，限制 5000 字符以内防止资源滥用")


class FeedbackRequest(BaseModel):
    feedback: bool
