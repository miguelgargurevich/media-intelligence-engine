"""HTML-based media extraction downloader."""

import re
from pathlib import Path
from typing import Optional

import httpx

from src.domain.value_objects.url import URL
from src.ports.downloader import IDownloader, DownloadResult


class HTMLExtractorDownloader(IDownloader):
    """Downloader that extracts media URLs from HTML pages."""

    @property
    def name(self) -> str:
        return "html_extraction"

    async def can_handle(self, url: URL) -> bool:
        """HTML extraction can be attempted on any URL."""
        return True

    async def download(
        self,
        url: URL,
        output_dir: Path,
        **kwargs,
    ) -> DownloadResult:
        """Extract video/audio URLs from HTML by inspecting meta tags and common patterns."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                },
            ) as client:
                response = await client.get(str(url))
                response.raise_for_status()
                html = response.text

            # Try to find video URLs in common patterns
            video_patterns = [
                # Open Graph video
                r'<meta\s+property=["\']og:video["\']\s+content=["\']([^"\']+)["\']',
                # Twitter card video
                r'<meta\s+name=["\']twitter:player:stream["\']\s+content=["\']([^"\']+)["\']',
                # Video element src
                r'<video[^>]*src=["\']([^"\']+)["\']',
                # Source elements
                r'<source[^>]*src=["\']([^"\']+)["\']',
                # JSON-LD embedded content
                r'"contentUrl"\s*:\s*"([^"]+)"',
                r'"embedUrl"\s*:\s*"([^"]+)"',
                # Direct video file links
                r'href=["\']([^"\']+\.(mp4|webm|mov|avi|mkv))["\']',
            ]

            media_urls: list[str] = []
            for pattern in video_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    media_url = match if isinstance(match, str) else match[0]
                    if media_url.startswith(("http://", "https://", "//")):
                        if media_url.startswith("//"):
                            media_url = f"https:{media_url}"
                        media_urls.append(media_url)

            if not media_urls:
                return DownloadResult.failure(
                    error="No media URLs found in HTML",
                    strategy=self.name,
                )

            # Download the first valid media URL
            media_url = media_urls[0]
            output_path = output_dir / f"html_media_{url.path.replace('/', '_')[:50]}.mp4"

            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                media_response = await client.get(media_url)
                media_response.raise_for_status()

                output_path.write_bytes(media_response.content)

            if output_path.exists() and output_path.stat().st_size > 0:
                return DownloadResult.success(
                    file_path=output_path,
                    strategy=self.name,
                )

            return DownloadResult.failure(
                error="Downloaded file is empty",
                strategy=self.name,
            )

        except httpx.HTTPStatusError as exc:
            return DownloadResult.failure(
                error=f"HTTP error: {exc.response.status_code}",
                strategy=self.name,
            )
        except httpx.TimeoutException:
            return DownloadResult.failure(
                error="Request timed out",
                strategy=self.name,
            )
        except Exception as exc:
            return DownloadResult.failure(
                error=f"HTML extraction error: {exc!s}",
                strategy=self.name,
            )