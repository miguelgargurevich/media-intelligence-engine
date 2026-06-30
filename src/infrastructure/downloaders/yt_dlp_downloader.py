"""yt-dlp-based downloader implementation."""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from src.domain.value_objects.url import URL
from src.infrastructure.config.settings import settings
from src.ports.downloader import IDownloader, DownloadResult


class YTDLPDownloader(IDownloader):
    """Downloader using yt-dlp for media from supported platforms."""

    @property
    def name(self) -> str:
        return "yt-dlp"

    async def can_handle(self, url: URL) -> bool:
        """yt-dlp can handle most video platforms."""
        return True  # Broad coverage

    async def download(
        self,
        url: URL,
        output_dir: Path,
        **kwargs,
    ) -> DownloadResult:
        """Download media using yt-dlp asynchronously."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            output_template = str(output_dir / "%(id)s.%(ext)s")

            cmd = [
                settings.yt_dlp_path,
                "--no-playlist",
                # Descarga el solver EJS (corre con deno) para resolver el
                # signature/n-challenge de YouTube; sin esto YouTube solo da imágenes.
                "--remote-components", "ejs:github",
                "--print", "after_move:filepath",
                "--print", "title",
                "--print", "duration",
                "--print", "width",
                "--print", "height",
                "-o", output_template,
                "--max-filesize", "500M",
            ]

            # yt-dlp reescribe el cookie jar al terminar; el archivo /app/cookies.txt
            # está montado READ-ONLY, así que escribir ahí lanza PermissionError y
            # tumba la descarga. Copiamos a una ruta escribible y usamos esa copia.
            cookies_path = Path("/app/cookies.txt")
            cookies_tmp = None
            if cookies_path.exists():
                fd, cookies_tmp = tempfile.mkstemp(prefix="ytck_", suffix=".txt")
                os.close(fd)
                shutil.copy(cookies_path, cookies_tmp)
                cmd += ["--cookies", cookies_tmp]

            # Proxy residencial SOLO para sitios que bloquean la IP del datacenter
            # (Instagram/Facebook/TikTok como fallback de gallery-dl). YouTube queda
            # directo: funciona y el proxy residencial puede romper el ejs-challenge.
            domain = (url.domain or "").lower()
            is_youtube = "youtube.com" in domain or "youtu.be" in domain
            if settings.download_proxy and not is_youtube:
                cmd += ["--proxy", settings.download_proxy]

            cmd.append(str(url))

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if cookies_tmp:
                try:
                    os.unlink(cookies_tmp)
                except OSError:
                    pass

            if process.returncode != 0:
                error_msg = stderr.decode().strip()[:500] if stderr else "Unknown error"
                return DownloadResult.failure(
                    error=f"yt-dlp failed: {error_msg}",
                    strategy=self.name,
                )

            return self._parse_output(stdout.decode(), output_dir)

        except FileNotFoundError:
            return DownloadResult.failure(
                error="yt-dlp not found. Install with: pip install yt-dlp",
                strategy=self.name,
            )
        except Exception as exc:
            return DownloadResult.failure(
                error=f"yt-dlp error: {exc!s}",
                strategy=self.name,
            )

    def _parse_output(self, output: str, output_dir: Path) -> DownloadResult:
        """Parse yt-dlp --print output.

        Output lines (--print order: after_move:filepath, title, duration, width, height):
          When file is downloaded/moved:
            line 0: after_move:filepath  (e.g., /path/to/file.mp4)
            line 1: title
            line 2: duration
            line 3: width
            line 4: height

          When file already exists (no move):
            line 0: (empty - after_move:filepath prints nothing)
            line 1: title
            line 2: duration
            line 3: width
            line 4: height
        """
        lines = output.strip().split("\n")
        cleaned = [l.strip() for l in lines if l.strip()]

        if not cleaned:
            return DownloadResult.failure(error="No output from yt-dlp", strategy=self.name)

        # Check if first line is a file path or a title
        first_line = cleaned[0]

        # If it ends with a video extension, it's a filepath
        video_exts = {".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4a", ".mp3", ".wav", ".flac"}
        is_filepath = any(first_line.lower().endswith(ext) for ext in video_exts) or "/" in first_line

        if is_filepath:
            filepath = Path(first_line)
            title = cleaned[1] if len(cleaned) > 1 else None
            duration = float(cleaned[2]) if len(cleaned) > 2 and cleaned[2].replace(".", "").replace("-", "").isdigit() else None
            width = int(cleaned[3]) if len(cleaned) > 3 and cleaned[3].isdigit() else None
            height = int(cleaned[4]) if len(cleaned) > 4 and cleaned[4].isdigit() else None
        else:
            # No filepath printed (file already existed) - find the file in output_dir
            title = first_line
            duration = float(cleaned[1]) if len(cleaned) > 1 and cleaned[1].replace(".", "").replace("-", "").isdigit() else None
            width = int(cleaned[2]) if len(cleaned) > 2 and cleaned[2].isdigit() else None
            height = int(cleaned[3]) if len(cleaned) > 3 and cleaned[3].isdigit() else None

            # Find the file by looking for the newest video file in output_dir
            filepath = self._find_file_by_title(output_dir, title) if title else None

        if filepath and filepath.exists() and filepath.stat().st_size > 0:
            return DownloadResult.success(
                file_path=filepath,
                strategy=self.name,
                title=title,
                duration=duration,
                width=width,
                height=height,
            )

        return DownloadResult.failure(
            error=f"File not found: {filepath}",
            strategy=self.name,
        )

    def _find_file_by_title(self, output_dir: Path, title: str) -> Optional[Path]:
        """Try to find the downloaded file by matching title."""
        if not output_dir.exists():
            return None

        files = sorted(output_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files:
            if f.is_file() and f.stat().st_size > 0:
                return f
        return None