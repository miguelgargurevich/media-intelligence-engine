"""Base vision provider with common utilities."""

from abc import ABC
from pathlib import Path
from typing import Optional

from src.ports.vision_provider import IVisionProvider, VisionAnalysis


class BaseVisionProvider(IVisionProvider, ABC):
    """Base class for vision providers with shared functionality."""

    def __init__(self, api_key: Optional[str] = None, model: str = "default") -> None:
        self._api_key = api_key
        self._model = model

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64."""
        import base64

        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_image_format(self, image_path: Path) -> str:
        """Get image MIME type from extension."""
        ext = image_path.suffix.lower()
        mapping = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return mapping.get(ext, "image/jpeg")