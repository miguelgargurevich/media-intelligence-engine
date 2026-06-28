"""Google Gemini Vision provider implementation."""

from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.vision_provider import VisionAnalysis
from src.infrastructure.vision.base import BaseVisionProvider


class GeminiVisionProvider(BaseVisionProvider):
    """Vision analysis using Google Gemini."""

    @property
    def provider_name(self) -> str:
        return "gemini"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    async def analyze_image(
        self,
        image_path: Path,
        prompt: str = "Describe this image in detail, including any text, code, commands, URLs, or technologies visible.",
        **kwargs,
    ) -> VisionAnalysis:
        try:
            import google.generativeai as genai

            if not self._api_key:
                return VisionAnalysis.failure(error="Gemini API key not configured", provider=self.provider_name)

            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model)

            image_data = self._encode_image(image_path)
            image_parts = [{"mime_type": self._get_image_format(image_path), "data": image_data}]

            response = await model.generate_content_async([prompt, image_parts[0]])

            return VisionAnalysis.success(
                description=response.text or "",
                provider=self.provider_name,
                model=self._model,
            )

        except ImportError:
            return VisionAnalysis.failure(error="Gemini SDK not installed. Run: pip install google-generativeai", provider=self.provider_name)
        except Exception as exc:
            return VisionAnalysis.failure(error=f"Gemini Vision error: {exc!s}", provider=self.provider_name)

    async def analyze_images_batch(self, image_paths: list[Path], prompt: str = "Describe what you see in this image.", max_concurrent: int = 5, **kwargs) -> list[VisionAnalysis]:
        import asyncio
        semaphore = asyncio.Semaphore(max_concurrent)
        async def _analyze_one(path: Path) -> VisionAnalysis:
            async with semaphore:
                return await self.analyze_image(path, prompt)
        tasks = [_analyze_one(p) for p in image_paths]
        return await asyncio.gather(*tasks, return_exceptions=False)