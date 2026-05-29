from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    scene_number: int
    start_time: str | None = None
    end_time: str | None = None
    description: str | None = None
    risk: str | None = None
    risk_level: str | None = None
    probability: float | None = None
    reason: str | None = None
    quote: str | None = None
    text_in_frame: str | None = None
    recommendation: str | None = None


class AnalysisSummary(BaseModel):
    total_scenes: int = 0
    risky_scenes: int = 0
    risk_categories: dict[str, int] = {}
    critical_count: int = 0
    warning_count: int = 0


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_file_id: str
    video_title: str | None = None
    duration: str | None = None
    analyzed_at: datetime | None = None
    summary: dict | None = None
    status: str
    created_at: datetime
    scenes: list[SceneResponse] = []


# --- Gemini response parsing schemas ---

class GeminiSceneRisk(BaseModel):
    risk: str | None = None
    risk_level: str | None = None
    probability: float | None = None
    reason: str | None = None
    quote: str | None = None
    text_in_frame: str | None = None
    recommendation: str | None = None


class GeminiScene(BaseModel):
    scene_number: int
    start_time: str | None = None
    end_time: str | None = None
    description: str | None = None
    risks: list[GeminiSceneRisk] = []


class GeminiAnalysisResult(BaseModel):
    video_title: str | None = None
    duration: str | None = None
    scenes: list[GeminiScene] = []
