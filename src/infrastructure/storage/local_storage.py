"""Local filesystem storage implementation."""

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.storage import IStorage


class LocalStorage(IStorage):
    """Storage backend using the local filesystem."""

    def __init__(self) -> None:
        self.base_path = settings.temp_dir
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save_file(self, source_path: Path, destination_path: str, **kwargs) -> Path:
        dest = self.base_path / destination_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        return dest

    async def read_file(self, path: str) -> bytes:
        full_path = self.base_path / path
        return full_path.read_bytes()

    async def delete_file(self, path: str) -> bool:
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def file_exists(self, path: str) -> bool:
        return (self.base_path / path).exists()

    async def list_files(self, directory: str, pattern: str = "*") -> list[str]:
        target = self.base_path / directory
        if not target.exists():
            return []
        return [str(p.relative_to(self.base_path)) for p in target.glob(pattern) if p.is_file()]

    async def get_temporary_path(self, prefix: str = "", suffix: str = "") -> Path:
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=str(self.base_path))
        import os
        os.close(fd)
        return Path(path)