"""FFmpeg-based screen recording for fallback media capture."""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.recorder import IRecorder, RecordingResult


class FFmpegScreenRecorder(IRecorder):
    """Records screen output using FFmpeg.

    Used as fallback when direct media download is not possible.
    Opens the URL in a headless browser, plays the content,
    and captures the screen + audio output.
    """

    async def record(
        self,
        url: str,
        output_path: Path,
        duration: Optional[float] = None,
        resolution: str = "1920x1080",
        fps: int = 30,
        **kwargs,
    ) -> RecordingResult:
        """Record screen with audio while playing media from URL."""
        try:
            # Step 1: Launch Playwright to play the media
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,  # Need display for recording
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle")

                # Try to find and auto-play video
                await page.evaluate("""
                    () => {
                        const videos = document.querySelectorAll('video');
                        videos.forEach(v => {
                            v.muted = false;
                            v.play().catch(() => {});
                        });
                    }
                """)

                # Step 2: Start FFmpeg screen recording
                width, height = resolution.split("x")

                # Detect display (macOS uses :0, Linux uses :99.0 or similar)
                display = ":99.0"  # Default for virtual framebuffer

                ffmpeg_cmd = [
                    settings.ffmpeg_path,
                    "-f", "x11grab",
                    "-video_size", resolution,
                    "-framerate", str(fps),
                    "-i", f"{display}+0,0",
                    "-f", "pulse",
                    "-i", "default",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "28",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-t", str(duration or 300),
                    "-y",
                    str(output_path),
                ]

                # Try macOS AVFoundation first, fallback to x11grab
                ffmpeg_macos_cmd = [
                    settings.ffmpeg_path,
                    "-f", "avfoundation",
                    "-video_size", resolution,
                    "-framerate", str(fps),
                    "-i", "1:0",  # Screen:Microphone
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "28",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-t", str(duration or 300),
                    "-y",
                    str(output_path),
                ]

                selected_cmd = ffmpeg_macos_cmd if sys_platform() == "darwin" else ffmpeg_cmd

                process = await asyncio.create_subprocess_exec(
                    *selected_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Wait for recording duration
                record_time = duration or 120
                await asyncio.sleep(record_time)

                # Stop recording
                process.terminate()
                await process.wait()

                await browser.close()

                if output_path.exists() and output_path.stat().st_size > 0:
                    return RecordingResult.success(
                        file_path=output_path,
                        duration=record_time,
                    )

                return RecordingResult.failure(
                    error="Recording file is empty or was not created",
                )

        except ImportError:
            return RecordingResult.failure(
                error="Playwright not installed",
            )
        except Exception as exc:
            return RecordingResult.failure(
                error=f"Screen recording error: {exc!s}",
            )


def sys_platform() -> str:
    """Detect OS platform."""
    import sys
    return sys.platform