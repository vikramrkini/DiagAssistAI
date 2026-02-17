from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

EMBEDDING_DIM = 1536


class GuidelineDoc(Base):
    __tablename__ = "guideline_docs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks = relationship("GuidelineChunk", back_populates="doc", cascade="all, delete-orphan")


class GuidelineChunk(Base):
    __tablename__ = "guideline_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("guideline_docs.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    specialty_tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    bm25_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    tsv: Mapped[str | None] = mapped_column(TSVECTOR)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    doc = relationship("GuidelineDoc", back_populates="chunks")
