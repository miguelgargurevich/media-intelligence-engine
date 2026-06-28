"""Storage interface for persisting analysis artifacts."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class IStorage(ABC):
    """Interface for storage backends.

    Implementations handle saving, retrieving, and managing
    analysis artifacts (downloads, recordings, frames, results).
    """

    @abstractmethod
    async def save_file(
        self,
        source_path: Path,
        destination_path: str,
        **kwargs,
    ) -> Path:
        """Save a file to storage.

        Args:
            source_path: Local path to the file.
            destination_path: Destination path in storage.
            **kwargs: Additional storage-specific options.

        Returns:
            Path to the saved file in storage.
        """
        ...

    @abstractmethod
    async def read_file(self, path: str) -> bytes:
        """Read a file from storage.

        Args:
            path: Path to the file in storage.

        Returns:
            File contents as bytes.
        """
        ...

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file from storage.

        Args:
            path: Path to the file in storage.

        Returns:
            True if deleted successfully.
        """
        ...

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if a file exists in storage.

        Args:
            path: Path to the file in storage.

        Returns:
            True if the file exists.
        """
        ...

    @abstractmethod
    async def list_files(self, directory: str, pattern: str = "*") -> list[str]:
        """List files in a storage directory.

        Args:
            directory: Directory path in storage.
            pattern: Glob pattern for filtering.

        Returns:
            List of file paths matching the pattern.
        """
        ...

    @abstractmethod
    async def get_temporary_path(self, prefix: str = "", suffix: str = "") -> Path:
        """Get a temporary path for storing intermediate files.

        Args:
            prefix: File name prefix.
            suffix: File extension (e.g., '.mp4').

        Returns:
            A temporary file path.
        """
        ...