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
            cmd = [
                settings.gallery_dl_path,
                "--directory", str(output_dir),
                "--filename", "{title}_{id}.{extension}",
                "--write-metadata",
                str(url),
            ]
            # Use cookies file if available (mounted volume / cookies.txt)
            cookies_path = Path("/app/cookies.txt")
            if cookies_path.exists():
                cmd.insert(1, "--cookies")
                cmd.insert(2, str(cookies_path))

            # Proxy residencial/móvil: Instagram/Twitter/etc. desafían la IP del
            # datacenter (devuelven "redirect to home") aun con sesión válida.
            # Rutear por una IP residencial hace que IG acepte la sesión.
            if settings.download_proxy:
                cmd.insert(1, "--proxy")
                cmd.insert(2, settings.download_proxy)

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

            # gallery-dl creates subdirs like ./gallery-dl/instagram/user/video.mp4
            # Search recursively for the most recently created media file (exclude .json metadata)
            media_extensions = {".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4a", ".mp3", ".wav", ".flac", ".jpg", ".jpeg", ".png", ".gif"}
            all_files = sorted(
                (p for p in output_dir.rglob("*") if p.is_file() and p.stat().st_size > 0 and p.suffix.lower() in media_extensions),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if all_files:
                return DownloadResult.success(
                    file_path=all_files[0],
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