"""Analysis result entity - the final structured output."""

from dataclasses import dataclass, field
from typing import Optional

from src.domain.value_objects.timestamp import TimelineEntry


@dataclass
class AnalysisResult:
    """Structured result of a complete media analysis.

    This is the final output of the pipeline, containing all
    extracted knowledge from the media content.
    """

    # Metadata
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None

    # Audio analysis
    transcript: Optional[str] = None
    transcript_segments: list[dict] = field(default_factory=list)

    # Visual analysis
    visual_summary: Optional[str] = None

    # Timeline
    timeline: list[TimelineEntry] = field(default_factory=list)

    # Extracted items
    commands: list[str] = field(default_factory=list)
    code_blocks: list[dict] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    # Summaries
    summary: Optional[str] = None
    markdown: Optional[str] = None
    html: Optional[str] = None

    # Raw analysis data
    raw_ocr_texts: list[str] = field(default_factory=list)
    raw_vision_descriptions: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if the analysis completed successfully."""
        return self.status == "completed"

    @property
    def has_transcript(self) -> bool:
        """Check if a transcript was generated."""
        return bool(self.transcript)

    @property
    def has_visual_data(self) -> bool:
        """Check if visual analysis was performed."""
        return bool(self.visual_summary) or bool(self.timeline)

    def to_dict(self) -> dict:
        """Convert analysis result to a dictionary for JSON serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "language": self.language,
            "source_url": self.source_url,
            "status": self.status,
            "error": self.error,
            "transcript": self.transcript,
            "transcript_segments": self.transcript_segments,
            "visual_summary": self.visual_summary,
            "timeline": [
                {
                    "timestamp": entry.timestamp,
                    "text": entry.text,
                    "ocr_text": entry.ocr_text,
                    "vision_description": entry.vision_description,
                    "commands": entry.commands or [],
                    "code_blocks": entry.code_blocks or [],
                    "urls": entry.urls or [],
                    "technologies": entry.technologies or [],
                    "keywords": entry.keywords or [],
                }
                for entry in self.timeline
            ],
            "commands": self.commands,
            "code_blocks": self.code_blocks,
            "urls": self.urls,
            "technologies": self.technologies,
            "keywords": self.keywords,
            "summary": self.summary,
            "markdown": self.markdown,
            "html": self.html,
        }