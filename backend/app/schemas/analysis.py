from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    scene_number: int
    start_time: str | None = None
    end_time: str | None = None
    description: str | None = None
    risk: str | None = None
    mode: str | None = None
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
    recommended_age_rating: str | None = None
    age_rating_reason: str | None = None
    age_rating_triggers: list[dict] = []
    entities: list[dict] = []
    markings_detected: list[dict] = []


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
    model_config = ConfigDict(extra="ignore")

    risk: str | None = None
    mode: str | None = None
    risk_level: str | None = None
    probability: float | None = None
    reason: str | None = None
    quote: str | None = None
    text_in_frame: str | None = None
    recommendation: str | None = None

    @field_validator("probability", mode="before")
    @classmethod
    def coerce_probability(cls, value):
        if value is None or value == "":
            return None
        return float(value)


class GeminiScene(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scene_number: int
    start_time: str | None = None
    end_time: str | None = None
    description: str | None = None
    risks: list[GeminiSceneRisk] = []


class GeminiAgeRatingTrigger(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scene_number: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    trigger: str | None = None
    reason: str | None = None


class GeminiEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str | None = None
    name: str | None = None
    scene_number: int | None = None
    context: str | None = None


class GeminiMarking(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str | None = None
    text: str | None = None
    scene_number: int | None = None
    start_time: str | None = None


class GeminiAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    video_title: str | None = None
    duration: str | None = None
    total_scenes_reviewed: int | None = None
    recommended_age_rating: str | None = None
    age_rating_reason: str | None = None
    age_rating_triggers: list[GeminiAgeRatingTrigger] = []
    entities: list[GeminiEntity] = []
    markings_detected: list[GeminiMarking] = []
    scenes: list[GeminiScene] = []
