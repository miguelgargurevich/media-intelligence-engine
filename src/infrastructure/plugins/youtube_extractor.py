"""YouTube-specific extractor plugin."""

from pathlib import Path
from typing import Any, Optional

from src.domain.value_objects.url import URL
from src.infrastructure.plugins.base_extractor import BaseExtractor
from src.ports.plugin import register_plugin


@register_plugin
class YouTubeExtractor(BaseExtractor):
    """Extractor for YouTube content."""

    @property
    def platform(self) -> str:
        return "youtube"

    @property
    def priority(self) -> int:
        return 10

    def can_handle(self, url: URL) -> bool:
        youtube_domains = {"youtube.com", "youtu.be", "m.youtube.com", "www.youtube.com"}
        return url.domain in youtube_domains

    async def extract(self, url: URL, output_dir: Path, **kwargs) -> dict[str, Any]:
        from src.infrastructure.downloaders.yt_dlp_downloader import YTDLPDownloader

        downloader = YTDLPDownloader()
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


@register_plugin
class GenericWebExtractor(BaseExtractor):
    """Fallback extractor for any web page."""

    @property
    def platform(self) -> str:
        return "generic_web"

    @property
    def priority(self) -> int:
        return 100

    def can_handle(self, url: URL) -> bool:
        return True

    async def extract(self, url: URL, output_dir: Path, **kwargs) -> dict[str, Any]:
        from src.infrastructure.downloaders.html_extractor import HTMLExtractorDownloader
        from src.infrastructure.downloaders.dom_extractor import DOMExtractorDownloader

        # Try HTML extraction first
        html_downloader = HTMLExtractorDownloader()
        result = await html_downloader.download(url, output_dir)
        if result.success:
            return {"success": True, "file_path": str(result.file_path), "strategy": "html", "platform": self.platform}

        # Fallback to DOM inspection
        dom_downloader = DOMExtractorDownloader()
        result = await dom_downloader.download(url, output_dir)
        if result.success:
            return {"success": True, "file_path": str(result.file_path), "strategy": "dom", "platform": self.platform}

        return {"success": False, "error": result.error, "platform": self.platform}