"""Response schemas for the API."""

from typing import Optional

from pydantic import BaseModel, Field


class TimelineEntryResponse(BaseModel):
    """A single entry in the analysis timeline."""

    timestamp: float = Field(..., description="Timestamp in seconds")
    text: Optional[str] = Field(None, description="Combined text from OCR and transcription")
    ocr_text: Optional[str] = Field(None, description="Text extracted via OCR at this timestamp")
    vision_description: Optional[str] = Field(None, description="Vision analysis description")
    commands: list[str] = Field(default_factory=list, description="Detected CLI commands")
    code_blocks: list[str] = Field(default_factory=list, description="Detected code blocks")
    urls: list[str] = Field(default_factory=list, description="Detected URLs")
    technologies: list[str] = Field(default_factory=list, description="Detected technologies")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")


class CodeBlockResponse(BaseModel):
    """A detected code block."""

    code: str = Field(..., description="The code content")
    language: Optional[str] = Field(None, description="Detected programming language")
    source: str = Field("unknown", description="Source of detection (ocr, vision)")


class AnalyzeResponse(BaseModel):
    """Response body for POST /analyze."""

    title: Optional[str] = Field(None, description="Title of the media content")
    description: Optional[str] = Field(None, description="Description of the media content")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    language: Optional[str] = Field(None, description="Detected language")
    source_url: Optional[str] = Field(None, description="Original source URL")
    status: str = Field("pending", description="Analysis status")
    error: Optional[str] = Field(None, description="Error message if failed")

    transcript: Optional[str] = Field(None, description="Full audio transcript")
    transcript_segments: list[dict] = Field(default_factory=list, description="Transcribed segments with timestamps")

    visual_summary: Optional[str] = Field(None, description="Summary of visual content")

    timeline: list[TimelineEntryResponse] = Field(default_factory=list, description="Timeline of extracted content")

    commands: list[str] = Field(default_factory=list, description="All detected CLI commands")
    code_blocks: list[CodeBlockResponse] = Field(default_factory=list, description="All detected code blocks")
    urls: list[str] = Field(default_factory=list, description="All detected URLs")
    technologies: list[str] = Field(default_factory=list, description="All detected technologies")
    keywords: list[str] = Field(default_factory=list, description="All extracted keywords")

    summary: Optional[str] = Field(None, description="Text summary of the analysis")
    markdown: Optional[str] = Field(None, description="Full analysis in Markdown format")
    html: Optional[str] = Field(None, description="Full analysis in HTML format")

    # Semantic enrichment (Phase 8 - LLM cascade)
    sentiment: Optional[str] = Field(None, description="POSITIVE | NEUTRAL | NEGATIVE")
    topic_type: Optional[str] = Field(None, description="tutorial | reunion | presentacion | demo | podcast | entrevista | short | otro")
    chapters: list[dict] = Field(default_factory=list, description="Content chapters with timestamps")
    highlights: list[dict] = Field(default_factory=list, description="Key highlight quotes")
    participants: list[str] = Field(default_factory=list, description="Detected participants")
    tasks: list[dict] = Field(default_factory=list, description="Extracted tasks with assignee and priority")
    agreements: list[dict] = Field(default_factory=list, description="Agreements and commitments")
    risks: list[dict] = Field(default_factory=list, description="Identified risks with impact")
    open_questions: list[str] = Field(default_factory=list, description="Unresolved questions")
    next_steps: list[str] = Field(default_factory=list, description="Action items and next steps")
    hashtags: list[str] = Field(default_factory=list, description="Relevant hashtags")
    follow_up_email: Optional[dict] = Field(None, description="Suggested follow-up email with subject and body")
    diagrams: list[dict] = Field(default_factory=list, description="Mermaid diagrams")


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = Field("ok", description="Service health status")
    version: str = Field("0.1.0", description="Application version")
    service: str = Field("media-intelligence-engine", description="Service name")


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error description")
    status_code: int = Field(400, description="HTTP status code")