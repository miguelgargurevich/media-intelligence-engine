"""Speech-to-text interface for audio transcription."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class TranscriptionSegment:
    """A segment of transcribed audio with timing."""

    def __init__(
        self,
        text: str,
        start: float,
        end: float,
        confidence: float = 1.0,
    ) -> None:
        self.text = text
        self.start = start
        self.end = end
        self.confidence = confidence

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
        }


class TranscriptionResult:
    """Result of audio transcription."""

    def __init__(
        self,
        success: bool,
        text: str = "",
        segments: list[TranscriptionSegment] = None,
        language: Optional[str] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.text = text
        self.segments = segments or []
        self.language = language
        self.duration = duration
        self.error = error

    @classmethod
    def failure(cls, error: str) -> "TranscriptionResult":
        """Create a failure result."""
        return cls(success=False, error=error)

    @classmethod
    def success(
        cls,
        text: str,
        segments: list[TranscriptionSegment] = None,
        language: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> "TranscriptionResult":
        """Create a success result."""
        return cls(
            success=True,
            text=text,
            segments=segments or [],
            language=language,
            duration=duration,
        )


class ISpeechToText(ABC):
    """Interface for speech-to-text / audio transcription engines."""

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model: str = "base",
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to the audio file.
            language: Language code (e.g., 'en', 'es'). Auto-detect if None.
            model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large').
            **kwargs: Additional transcription options.

        Returns:
            TranscriptionResult with full text and segments.
        """
        ...