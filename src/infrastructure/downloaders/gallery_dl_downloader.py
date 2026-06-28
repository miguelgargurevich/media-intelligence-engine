"""gallery-dl downloader implementation (good for Instagram, Twitter, etc.)."""

import asyncio
import json
from pathlib import Path
from typing import Optional

from src.domain.value_objects.url import URL
from src.infrastructure.config.settings import settings
from src.ports.downloader import IDownloader, DownloadResult


class GalleryDLDownloader(IDownloader):
    """Downloader using gallery-dl for image/video galleries (Instagram, etc.)."""

    @property
    def name(self) -> str:
        return "gallery-dl"

    async def can_handle(self, url: URL) -> bool:
        """gallery-dl handles Instagram, Twitter, etc."""
        gallery_domains = {"instagram.com", "twitter.com", "x.com", "tumblr.com", "pinterest.com"}
        return any(d in url.domain for d in gallery_domains)

    async def download(
        self,
        url: URL,
        output_dir: Path,
        **kwargs,
    ) -> DownloadResult:
        """Download media using gallery-dl."""
        try:
            # gallery-dl can output JSON metadata with --writer
            cmd = [
                settings.gallery_dl_path,
                "--directory", str(output_dir),
                "--filename", "{title}_{id}.{extension}",
                "--write-metadata",
                str(url),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                return DownloadResult.failure(
                    error=f"gallery-dl failed: {error_msg}",
                    strategy=self.name,
                )

            # gallery-dl outputs paths of downloaded files
            output = stdout.decode().strip()
            if not output:
                return DownloadResult.failure(
                    error="No output from gallery-dl",
                    strategy=self.name,
                )

            # Find the most recently created file in output dir
            files = sorted(output_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                return DownloadResult.success(
                    file_path=files[0],
                    strategy=self.name,
                )

            return DownloadResult.failure(
                error="No files found after gallery-dl download",
                strategy=self.name,
            )

        except FileNotFoundError:
            return DownloadResult.failure(
                error="gallery-dl not found. Install with: pip install gallery-dl",
                strategy=self.name,
            )
        except Exception as exc:
            return DownloadResult.failure(
                error=f"gallery-dl error: {exc!s}",
                strategy=self.name,
            )