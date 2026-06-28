"""Timestamp value objects for timeline management."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TimeRange:
    """A time range with start and end in seconds."""

    start: float
    end: float

    def __post_init__(self) -> None:
        """Validate time range."""
        if self.start < 0:
            msg = f"Start time must be non-negative, got {self.start}"
            raise ValueError(msg)
        if self.end <= self.start:
            msg = f"End time ({self.end}) must be > start time ({self.start})"
            raise ValueError(msg)

    @property
    def duration(self) -> float:
        """Return duration in seconds."""
        return self.end - self.start

    def contains(self, timestamp: float) -> bool:
        """Check if timestamp falls within this range."""
        return self.start <= timestamp <= self.end

    def overlaps(self, other: "TimeRange") -> bool:
        """Check if this range overlaps with another."""
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class TimelineEntry:
    """An entry in the media timeline with extracted content."""

    timestamp: float
    text: Optional[str] = None
    ocr_text: Optional[str] = None
    vision_description: Optional[str] = None
    commands: list[str] = None
    code_blocks: list[str] = None
    urls: list[str] = None
    technologies: list[str] = None
    keywords: list[str] = None
    frame_path: Optional[str] = None

    def __post_init__(self) -> None:
        if self.commands is None:
            object.__setattr__(self, "commands", [])
        if self.code_blocks is None:
            object.__setattr__(self, "code_blocks", [])
        if self.urls is None:
            object.__setattr__(self, "urls", [])
        if self.technologies is None:
            object.__setattr__(self, "technologies", [])
        if self.keywords is None:
            object.__setattr__(self, "keywords", [])