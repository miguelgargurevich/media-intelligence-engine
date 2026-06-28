"""Request schemas for the API."""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""

    url: str = Field(
        ...,
        description="URL of the media content to analyze",
        examples=["https://www.youtube.com/watch?v=example"],
    )
    fps: Optional[float] = Field(
        default=None,
        description="Frames per second for extraction (default: from config)",
        ge=0.1,
        le=30.0,
    )
    language: Optional[str] = Field(
        default=None,
        description="Language code for transcription (default: from config)",
        examples=["en", "es", "fr", "de"],
    )
    vision_provider: Optional[str] = Field(
        default=None,
        description="Vision AI provider to use (default: from config)",
        examples=["openai", "gemini", "claude"],
    )
    max_duration: Optional[int] = Field(
        default=None,
        description="Maximum duration in seconds to process",
        ge=1,
        le=3600,
    )