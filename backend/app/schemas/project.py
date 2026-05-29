from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str


class FolderCreate(BaseModel):
    name: str
    project_id: str


class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    project_id: str
    created_at: datetime


class AnalysisBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    summary: dict | None = None
    analyzed_at: datetime | None = None


class VideoFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    size: int
    status: str
    progress: int
    project_id: str
    folder_id: str | None = None
    storage_path: str | None = None
    analysis_id: str | None = None
    analysis: AnalysisBrief | None = None
    created_at: datetime
    updated_at: datetime


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    files_count: int = 0


class ProjectDetailResponse(ProjectResponse):
    folders: list[FolderResponse] = []
    files: list[VideoFileResponse] = []
