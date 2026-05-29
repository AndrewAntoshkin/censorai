import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    video_file_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    video_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    scenes: Mapped[list["Scene"]] = relationship(back_populates="analysis", cascade="all, delete-orphan", order_by="Scene.scene_number")

    @property
    def summary(self) -> dict | None:
        if self.summary_json:
            import json
            return json.loads(self.summary_json)
        return None

    @summary.setter
    def summary(self, value: dict | None) -> None:
        if value is not None:
            import json
            self.summary_json = json.dumps(value, ensure_ascii=False)
        else:
            self.summary_json = None


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_in_frame: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    analysis: Mapped["Analysis"] = relationship(back_populates="scenes")
