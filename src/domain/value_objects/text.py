"""Text-related value objects."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TextBlock:
    """A block of extracted text with metadata."""

    text: str
    confidence: float = 1.0
    language: Optional[str] = None
    source: str = "unknown"  # 'ocr', 'whisper', 'vision', 'metadata'
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"Confidence must be between 0 and 1, got {self.confidence}"
            raise ValueError(msg)

    @property
    def is_code(self) -> bool:
        """Check if text appears to be code."""
        import re

        code_patterns = [
            r"def\s+\w+\s*\(",
            r"class\s+\w+",
            r"import\s+\w+",
            r"const\s+\w+\s*=",
            r"function\s+\w+",
            r"<\/?\w+[^>]*>",
            r"SELECT\s+.*\s+FROM",
            r"\{\s*\"\w+\"\s*:",
        ]
        return any(re.search(p, self.text) for p in code_patterns)

    @property
    def is_url(self) -> bool:
        """Check if text is a URL."""
        import re

        url_pattern = r"https?://[^\s/$.?#].[^\s]*"
        return bool(re.match(url_pattern, self.text.strip()))

    @property
    def is_command(self) -> bool:
        """Check if text appears to be a CLI command."""
        import re

        command_patterns = [
            r"^\$\s+",
            r"^npm\s+",
            r"^pip\s+",
            r"^git\s+",
            r"^docker\s+",
            r"^kubectl\s+",
            r"^ssh\s+",
            r"^curl\s+",
        ]
        return any(re.match(p, self.text.strip()) for p in command_patterns)


@dataclass(frozen=True)
class ExtractedCode:
    """Code block extracted from media."""

    code: str
    language: Optional[str] = None
    confidence: float = 1.0
    source: str = "unknown"
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass(frozen=True)
class ExtractedURL:
    """URL extracted from media content."""

    url: str
    context: Optional[str] = None
    source: str = "unknown"  # 'ocr', 'vision', 'metadata'