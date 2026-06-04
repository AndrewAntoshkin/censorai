from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
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


class BlobUploadRequest(BaseModel):
    """After client upload to Blob or R2/S3 presigned PUT."""

    filename: str
    size: int
    blob_url: str | None = None
    storage_path: str | None = None
    duration_seconds: float | None = None


class PresignUploadRequest(BaseModel):
    filename: str
    size: int
    project_id: str | None = None
    content_type: str | None = None


class PresignUploadResponse(BaseModel):
    upload_url: str
    storage_path: str
    method: str = "PUT"
    headers: dict[str, str]


class UploadStrategyResponse(BaseModel):
    method: str
    blob_available: bool = False
    object_storage: bool = False
    message: str | None = None


class ChunkUploadInitRequest(BaseModel):
    filename: str
    size: int
    project_id: str | None = None
    folder_id: str | None = None
    duration_seconds: float | None = None


class AssignProjectRequest(BaseModel):
    project_id: str


class ChunkUploadInitResponse(BaseModel):
    session_id: str
    chunk_size: int
    total_parts: int


class ChunkUploadStatusResponse(BaseModel):
    session_id: str
    received_parts: list[int]
    total_parts: int
    complete: bool


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
