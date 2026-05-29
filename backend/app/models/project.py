import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class VideoStatus(str, enum.Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    ERROR = "error"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    folders: Mapped[list["Folder"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    files: Mapped[list["VideoFile"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="folders")
    files: Mapped[list["VideoFile"]] = relationship(back_populates="folder", cascade="all, delete-orphan")


class VideoFile(Base):
    __tablename__ = "video_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), default=VideoStatus.UPLOADING.value)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    folder_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    analysis_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="files")
    folder: Mapped["Folder | None"] = relationship(back_populates="files")
    analysis: Mapped["Analysis | None"] = relationship(foreign_keys=[analysis_id], lazy="selectin")
