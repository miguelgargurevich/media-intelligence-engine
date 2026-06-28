"""OpenAI GPT Vision provider implementation."""

import asyncio
from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.vision_provider import VisionAnalysis
from src.infrastructure.vision.base import BaseVisionProvider


class GPTVisionProvider(BaseVisionProvider):
    """Vision analysis using OpenAI GPT-4o / GPT-4 Vision."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    async def analyze_image(
        self,
        image_path: Path,
        prompt: str = "Describe this image in detail, including any text, code, commands, URLs, or technologies visible.",
        **kwargs,
    ) -> VisionAnalysis:
        """Analyze image using OpenAI GPT Vision."""
        try:
            from openai import AsyncOpenAI

            if not self._api_key:
                return VisionAnalysis.failure(
                    error="OpenAI API key not configured",
                    provider=self.provider_name,
                )

            client = AsyncOpenAI(api_key=self._api_key)
            base64_image = self._encode_image(image_path)
            image_format = self._get_image_format(image_path)

            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_format};base64,{base64_image}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,
            )

            description = response.choices[0].message.content or ""

            return VisionAnalysis.success(
                description=description,
                provider=self.provider_name,
                model=self._model,
            )

        except ImportError:
            return VisionAnalysis.failure(
                error="OpenAI SDK not installed. Run: pip install openai",
                provider=self.provider_name,
            )
        except Exception as exc:
            return VisionAnalysis.failure(
                error=f"OpenAI Vision error: {exc!s}",
                provider=self.provider_name,
            )

    async def analyze_images_batch(
        self,
        image_paths: list[Path],
        prompt: str = "Describe what you see in this image.",
        max_concurrent: int = 5,
        **kwargs,
    ) -> list[VisionAnalysis]:
        """Analyze multiple images with limited concurrency."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _analyze_one(path: Path) -> VisionAnalysis:
            async with semaphore:
                return await self.analyze_image(path, prompt)

        tasks = [_analyze_one(p) for p in image_paths]
        return await asyncio.gather(*tasks, return_exceptions=False)