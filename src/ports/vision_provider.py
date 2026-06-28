"""Vision provider interface - pluggable AI vision analysis."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class VisionAnalysis:
    """Result of vision analysis on an image."""

    def __init__(
        self,
        success: bool,
        description: str = "",
        labels: list[str] = None,
        text_detected: str = "",
        technologies: list[str] = None,
        commands: list[str] = None,
        urls: list[str] = None,
        error: Optional[str] = None,
        provider: str = "unknown",
        model: str = "unknown",
    ) -> None:
        self.success = success
        self.description = description
        self.labels = labels or []
        self.text_detected = text_detected
        self.technologies = technologies or []
        self.commands = commands or []
        self.urls = urls or []
        self.error = error
        self.provider = provider
        self.model = model

    @classmethod
    def failure(cls, error: str, provider: str = "unknown") -> "VisionAnalysis":
        """Create a failure result."""
        return cls(success=False, error=error, provider=provider)

    @classmethod
    def success(
        cls,
        description: str,
        provider: str = "unknown",
        model: str = "unknown",
        labels: list[str] = None,
        text_detected: str = "",
        technologies: list[str] = None,
        commands: list[str] = None,
        urls: list[str] = None,
    ) -> "VisionAnalysis":
        """Create a success result."""
        return cls(
            success=True,
            description=description,
            provider=provider,
            model=model,
            labels=labels or [],
            text_detected=text_detected,
            technologies=technologies or [],
            commands=commands or [],
            urls=urls or [],
        )


class IVisionProvider(ABC):
    """Interface for AI vision analysis providers.

    Implementations connect to different AI services (GPT, Gemini, Claude, etc.)
    to analyze images and extract structured information.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the vision provider (e.g., 'openai', 'gemini')."""
        ...

    @abstractmethod
    async def analyze_image(
        self,
        image_path: Path,
        prompt: str = "Describe this image in detail, including any text, code, commands, URLs, or technologies visible.",
        **kwargs,
    ) -> VisionAnalysis:
        """Analyze a single image using AI vision.

        Args:
            image_path: Path to the image file.
            prompt: Custom prompt for the vision model.
            **kwargs: Additional provider-specific options.

        Returns:
            VisionAnalysis with structured information.
        """
        ...

    @abstractmethod
    async def analyze_images_batch(
        self,
        image_paths: list[Path],
        prompt: str = "Describe what you see in this image.",
        max_concurrent: int = 5,
        **kwargs,
    ) -> list[VisionAnalysis]:
        """Analyze multiple images, potentially in parallel.

        Args:
            image_paths: List of paths to image files.
            prompt: Custom prompt for the vision model.
            max_concurrent: Maximum concurrent API calls.
            **kwargs: Additional provider-specific options.

        Returns:
            List of VisionAnalysis results.
        """
        ...