"""DeepSeek Vision provider implementation using HTTP API."""

from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.vision_provider import VisionAnalysis
from src.infrastructure.vision.base import BaseVisionProvider


class DeepSeekVisionProvider(BaseVisionProvider):
    """Vision analysis using DeepSeek (compatible with OpenAI API format)."""

    @property
    def provider_name(self) -> str:
        return "deepseek"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
        )

    async def analyze_image(
        self,
        image_path: Path,
        prompt: str = "Describe this image in detail, including any text, code, commands, URLs, or technologies visible.",
        **kwargs,
    ) -> VisionAnalysis:
        """Analyze image using DeepSeek VL via HTTP API."""
        try:
            import httpx

            if not self._api_key:
                return VisionAnalysis.failure(
                    error="DeepSeek API key not configured",
                    provider=self.provider_name,
                )

            base64_image = self._encode_image(image_path)
            image_format = self._get_image_format(image_path)

            url = "https://api.deepseek.com/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_format};base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 1000,
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                description = data["choices"][0]["message"]["content"]
                return VisionAnalysis.success(
                    description=description or "",
                    provider=self.provider_name,
                    model=self._model,
                )
            else:
                return VisionAnalysis.failure(
                    error=f"DeepSeek API unexpected response: {data}",
                    provider=self.provider_name,
                )

        except ImportError:
            return VisionAnalysis.failure(
                error="httpx not installed",
                provider=self.provider_name,
            )
        except Exception as exc:
            return VisionAnalysis.failure(
                error=f"DeepSeek Vision error: {exc!s}",
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
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _analyze_one(path: Path) -> VisionAnalysis:
            async with semaphore:
                return await self.analyze_image(path, prompt)

        tasks = [_analyze_one(p) for p in image_paths]
        return await asyncio.gather(*tasks, return_exceptions=False)