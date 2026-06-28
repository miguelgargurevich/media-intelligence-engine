"""Instagram-specific extractor plugin."""

from pathlib import Path
from typing import Any

from src.domain.value_objects.url import URL
from src.infrastructure.plugins.base_extractor import BaseExtractor
from src.ports.plugin import register_plugin


@register_plugin
class InstagramExtractor(BaseExtractor):
    """Extractor for Instagram content (reels, posts, stories)."""

    @property
    def platform(self) -> str:
        return "instagram"

    @property
    def priority(self) -> int:
        return 15

    def can_handle(self, url: URL) -> bool:
        instagram_domains = {"instagram.com", "www.instagram.com"}
        return url.domain in instagram_domains

    async def extract(self, url: URL, output_dir: Path, **kwargs) -> dict[str, Any]:
        from src.infrastructure.downloaders.gallery_dl_downloader import GalleryDLDownloader

        downloader = GalleryDLDownloader()
        result = await downloader.download(url, output_dir)
        return {
            "success": result.success,
            "file_path": str(result.file_path) if result.file_path else None,
            "title": result.title,
            "duration": result.duration,
            "width": result.width,
            "height": result.height,
            "error": result.error,
            "platform": self.platform,
        }