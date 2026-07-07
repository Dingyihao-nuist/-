"""数据模型 - 知识库文档 & 文档块"""

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)  # pdf | docx | txt | md | csv | xlsx
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="processing")  # processing | ready | error
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    uploader = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)  # JSON 字符串
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    document = relationship("Document", back_populates="chunks")
