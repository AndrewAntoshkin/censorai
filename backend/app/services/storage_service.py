import logging
import mimetypes
import shutil
import uuid
from pathlib import Path

from app.core.config import settings
from app.services.object_storage import (
    build_object_key,
    delete_object,
    object_storage_enabled,
    upload_bytes,
    upload_file,
)

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._use_s3 = object_storage_enabled()
        if self._use_s3:
            logger.info("Object storage enabled (bucket=%s)", settings.S3_BUCKET)

    def get_project_dir(self, project_id: str) -> Path:
        project_dir = self.upload_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    async def save_upload(self, project_id: str, filename: str, content: bytes) -> str:
        if self._use_s3:
            key = build_object_key(project_id, filename)
            content_type = mimetypes.guess_type(filename)[0] or "video/mp4"
            return upload_bytes(key, content, content_type=content_type)

        project_dir = self.get_project_dir(project_id)
        file_id = uuid.uuid4()
        ext = Path(filename).suffix
        storage_filename = f"{file_id}{ext}"
        file_path = project_dir / storage_filename
        file_path.write_bytes(content)
        return str(file_path)

    async def save_upload_from_path(
        self, project_id: str, filename: str, source_path: Path
    ) -> str:
        if self._use_s3:
            key = build_object_key(project_id, filename)
            content_type = mimetypes.guess_type(filename)[0] or "video/mp4"
            return upload_file(key, source_path, content_type=content_type)

        project_dir = self.get_project_dir(project_id)
        file_id = uuid.uuid4()
        ext = Path(filename).suffix
        dest = project_dir / f"{file_id}{ext}"
        shutil.copyfile(source_path, dest)
        return str(dest)

    def get_file_path(self, storage_path: str) -> Path:
        return Path(storage_path)

    async def delete_file(self, storage_path: str) -> None:
        if storage_path.startswith("s3://"):
            delete_object(storage_path)
            return
        path = Path(storage_path)
        if path.exists():
            path.unlink()

    async def delete_project_dir(self, project_id: str) -> None:
        if self._use_s3:
            from app.services.object_storage import delete_objects_with_prefix

            delete_objects_with_prefix(f"projects/{project_id}/")
            return
        project_dir = self.upload_dir / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)

    async def move_file_to_project(self, storage_path: str, project_id: str) -> str:
        if storage_path.startswith(("http://", "https://", "s3://")):
            return storage_path

        source = Path(storage_path)
        if not source.is_file():
            return storage_path

        dest_dir = self.get_project_dir(project_id)
        dest = dest_dir / source.name
        if source.resolve() == dest.resolve():
            return storage_path

        shutil.move(str(source), str(dest))
        return str(dest)


storage_service = StorageService()
