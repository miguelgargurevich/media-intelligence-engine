"""PaddleOCR implementation for text extraction from frames."""

from pathlib import Path
from typing import Optional

from src.domain.value_objects.text import TextBlock
from src.infrastructure.config.settings import settings
from src.ports.ocr_engine import IOCREngine, OCRResult


class PaddleOCREngine(IOCREngine):
    """OCR engine using PaddleOCR for multilingual text detection."""

    def __init__(self) -> None:
        self._ocr = None

    async def _get_ocr(self):
        """Lazy-load PaddleOCR (heavy import)."""
        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=settings.ocr_lang.split(",")[0],
                use_gpu=settings.ocr_device == "gpu",
                show_log=False,
            )
        return self._ocr

    async def extract_text(self, image_path: Path, language: str = "en") -> OCRResult:
        """Extract text from a single image."""
        try:
            ocr = await self._get_ocr()
            result = ocr.ocr(str(image_path))

            if not result or not result[0]:
                return OCRResult.success(
                    text_blocks=[],
                    full_text="",
                )

            text_blocks: list[TextBlock] = []
            texts: list[str] = []

            for line in result[0]:
                if line and len(line) >= 2:
                    bbox, (text, confidence) = line[0], line[1]
                    text_blocks.append(
                        TextBlock(
                            text=text,
                            confidence=float(confidence),
                            language=language,
                            source="ocr",
                        )
                    )
                    texts.append(text)

            return OCRResult.success(
                text_blocks=text_blocks,
                full_text=" ".join(texts),
            )

        except ImportError:
            return OCRResult.failure(
                error="PaddleOCR not installed. Run: pip install paddlepaddle paddleocr",
            )
        except Exception as exc:
            return OCRResult.failure(
                error=f"OCR error: {exc!s}",
            )

    async def extract_text_batch(
        self,
        image_paths: list[Path],
        language: str = "en",
        max_workers: int = 4,
    ) -> list[OCRResult]:
        """Extract text from multiple images sequentially (PaddleOCR handles batching internally)."""
        results: list[OCRResult] = []
        for img_path in image_paths:
            result = await self.extract_text(img_path, language)
            results.append(result)
        return results