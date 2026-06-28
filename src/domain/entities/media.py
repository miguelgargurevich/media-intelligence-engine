"""Media entities representing the core domain objects."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.domain.enums.media_type import MediaType
from src.domain.value_objects.url import URL


@dataclass
class Media:
    """Represents a media file to be analyzed."""

    source_url: URL
    media_type: MediaType = MediaType.UNKNOWN
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    language: Optional[str] = None

    @property
    def is_downloaded(self) -> bool:
        """Check if media has been downloaded."""
        return self.file_path is not None and self.file_path.exists()

    @property
    def has_audio(self) -> bool:
        """Check if audio has been extracted."""
        return self.audio_path is not None and self.audio_path.exists()

    @property
    def resolution(self) -> Optional[str]:
        """Return resolution string if dimensions are available."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None


@dataclass
class Frame:
    """A single frame extracted from media."""

    index: int
    timestamp: float
    file_path: Path
    width: Optional[int] = None
    height: Optional[int] = None
    ocr_text: Optional[str] = None
    vision_description: Optional[str] = None

    @property
    def exists(self) -> bool:
        """Check if frame file exists on disk."""
        return self.file_path.exists()

    @property
    def filename(self) -> str:
        """Return the filename of the frame."""
        return self.file_path.name


@dataclass
class AudioTrack:
    """Extracted audio track from media."""

    file_path: Path
    duration: float
    sample_rate: int = 16000
    channels: int = 1
    format: str = "wav"

    @property
    def exists(self) -> bool:
        """Check if audio file exists on disk."""
        return self.file_path.exists()


@dataclass
class FrameCollection:
    """Collection of extracted frames with metadata."""

    frames: list[Frame] = field(default_factory=list)
    fps: float = 1.0
    total_frames: int = 0
    source_duration: Optional[float] = None

    def add_frame(self, frame: Frame) -> None:
        """Add a frame to the collection."""
        self.frames.append(frame)
        self.total_frames = len(self.frames)

    def get_frame_at(self, timestamp: float) -> Optional[Frame]:
        """Get the closest frame to a given timestamp."""
        if not self.frames:
            return None
        return min(self.frames, key=lambda f: abs(f.timestamp - timestamp))

    def get_frames_in_range(self, start: float, end: float) -> list[Frame]:
        """Get all frames within a time range."""
        return [f for f in self.frames if start <= f.timestamp <= end]

    @property
    def key_frames(self) -> list[Frame]:
        """Return evenly spaced subset for vision analysis (max 20)."""
        if len(self.frames) <= 20:
            return self.frames
        step = len(self.frames) // 20
        return [self.frames[i] for i in range(0, len(self.frames), step)]