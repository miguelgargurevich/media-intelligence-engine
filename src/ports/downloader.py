"""Downloader interface - strategy pattern for media download."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.domain.value_objects.url import URL


class DownloadResult:
    """Result of a download attempt."""

    def __init__(
        self,
        success: bool,
        file_path: Optional[Path] = None,
        title: Optional[str] = None,
        duration: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        error: Optional[str] = None,
        strategy: str = "unknown",
    ) -> None:
        self.success = success
        self.file_path = file_path
        self.title = title
        self.duration = duration
        self.width = width
        self.height = height
        self.error = error
        self.strategy = strategy

    @classmethod
    def failure(cls, error: str, strategy: str = "unknown") -> "DownloadResult":
        """Create a failure result."""
        return cls(success=False, error=error, strategy=strategy)

    @classmethod
    def success(
        cls,
        file_path: Path,
        strategy: str = "unknown",
        title: Optional[str] = None,
        duration: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "DownloadResult":
        """Create a success result."""
        return cls(
            success=True,
            file_path=file_path,
            strategy=strategy,
            title=title,
            duration=duration,
            width=width,
            height=height,
        )


class IDownloader(ABC):
    """Interface for media downloaders.

    Implementations should handle downloading media from specific sources
    or using specific strategies. The system tries multiple downloaders
    in order until one succeeds.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this downloader."""
        ...

    @abstractmethod
    async def can_handle(self, url: URL) -> bool:
        """Check if this downloader can handle the given URL."""
        ...

    @abstractmethod
    async def download(
        self,
        url: URL,
        output_dir: Path,
        **kwargs,
    ) -> DownloadResult:
        """Attempt to download media from the URL.

        Args:
            url: The URL to download from.
            output_dir: Directory to save downloaded content.
            **kwargs: Additional downloader-specific options.

        Returns:
            DownloadResult indicating success or failure.
        """
        ...