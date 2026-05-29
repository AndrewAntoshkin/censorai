import os
import shutil
import uuid
from pathlib import Path

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: str) -> Path:
        project_dir = self.upload_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    async def save_upload(self, project_id: str, filename: str, content: bytes) -> str:
        project_dir = self.get_project_dir(project_id)
        file_id = uuid.uuid4()
        ext = Path(filename).suffix
        storage_filename = f"{file_id}{ext}"
        file_path = project_dir / storage_filename
        file_path.write_bytes(content)
        return str(file_path)

    def get_file_path(self, storage_path: str) -> Path:
        return Path(storage_path)

    async def delete_file(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()

    async def delete_project_dir(self, project_id: str) -> None:
        project_dir = self.upload_dir / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)


storage_service = StorageService()
