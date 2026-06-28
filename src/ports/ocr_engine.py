"""OCR engine interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.domain.value_objects.text import TextBlock


class OCRResult:
    """Result of OCR processing on an image."""

    def __init__(
        self,
        success: bool,
        text_blocks: list[TextBlock] = None,
        full_text: str = "",
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.text_blocks = text_blocks or []
        self.full_text = full_text
        self.error = error

    @classmethod
    def failure(cls, error: str) -> "OCRResult":
        """Create a failure result."""
        return cls(success=False, error=error)

    @classmethod
    def success(
        cls,
        text_blocks: list[TextBlock],
        full_text: str = "",
    ) -> "OCRResult":
        """Create a success result."""
        return cls(
            success=True,
            text_blocks=text_blocks,
            full_text=full_text or " ".join(t.text for t in text_blocks),
        )


class IOCREngine(ABC):
    """Interface for OCR (Optical Character Recognition) engines.

    Implementations extract text from images and frames.
    """

    @abstractmethod
    async def extract_text(self, image_path: Path, language: str = "en") -> OCRResult:
        """Extract text from an image file.

        Args:
            image_path: Path to the image file.
            language: Language hint for OCR (e.g., 'en', 'es').

        Returns:
            OCRResult containing extracted text blocks.
        """
        ...

    @abstractmethod
    async def extract_text_batch(
        self,
        image_paths: list[Path],
        language: str = "en",
        max_workers: int = 4,
    ) -> list[OCRResult]:
        """Extract text from multiple images in parallel.

        Args:
            image_paths: List of paths to image files.
            language: Language hint for OCR.
            max_workers: Maximum number of parallel workers.

        Returns:
            List of OCRResult for each image.
        """
        ...