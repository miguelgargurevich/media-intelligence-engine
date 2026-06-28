"""Recorder interface - screen recording for fallback strategy."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class RecordingResult:
    """Result of a screen recording attempt."""

    def __init__(
        self,
        success: bool,
        file_path: Optional[Path] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.file_path = file_path
        self.duration = duration
        self.error = error

    @classmethod
    def failure(cls, error: str) -> "RecordingResult":
        """Create a failure result."""
        return cls(success=False, error=error)

    @classmethod
    def success(
        cls,
        file_path: Path,
        duration: Optional[float] = None,
    ) -> "RecordingResult":
        """Create a success result."""
        return cls(success=True, file_path=file_path, duration=duration)


class IRecorder(ABC):
    """Interface for screen recording functionality.

    Used as a fallback when direct download is not possible.
    Opens the page in a browser, plays the media, and records
    the screen output using FFmpeg.
    """

    @abstractmethod
    async def record(
        self,
        url: str,
        output_path: Path,
        duration: Optional[float] = None,
        resolution: str = "1920x1080",
        fps: int = 30,
        **kwargs,
    ) -> RecordingResult:
        """Record screen while playing media from URL.

        Args:
            url: The URL to navigate to and record.
            output_path: Path where the recording will be saved.
            duration: Maximum recording duration in seconds (None = auto-detect).
            resolution: Recording resolution (e.g., '1920x1080').
            fps: Frames per second for recording.
            **kwargs: Additional recorder-specific options.

        Returns:
            RecordingResult indicating success or failure.
        """
        ...