import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class UploadChunkSession(Base):
    __tablename__ = "upload_chunk_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    folder_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    received_parts_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    part_urls_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
