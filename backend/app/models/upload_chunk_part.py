"""Chunk bytes for resumable uploads (Vercel: avoids many small Blob objects)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UploadChunkPart(Base):
    __tablename__ = "upload_chunk_parts"

    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False
    )
    part_index: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
