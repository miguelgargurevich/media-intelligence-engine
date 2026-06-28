"""DOM-based media extraction using Playwright."""

import asyncio
from pathlib import Path
from typing import Optional

from src.domain.value_objects.url import URL
from src.ports.downloader import IDownloader, DownloadResult


class DOMExtractorDownloader(IDownloader):
    """Downloader that uses Playwright to inspect DOM for video sources."""

    @property
    def name(self) -> str:
        return "dom_inspection"

    async def can_handle(self, url: URL) -> bool:
        """DOM inspection can be attempted on any URL."""
        return True

    async def download(
        self,
        url: URL,
        output_dir: Path,
        **kwargs,
    ) -> DownloadResult:
        """Open page in headless browser and extract video source from DOM."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                await page.goto(str(url), wait_until="domcontentloaded", timeout=30000)

                # Wait a bit for dynamic content
                await asyncio.sleep(3)

                # Find video elements and extract sources
                video_sources = await page.evaluate("""
                    () => {
                        const sources = [];
                        // Direct video elements
                        document.querySelectorAll('video').forEach(v => {
                            if (v.src) sources.push(v.src);
                            v.querySelectorAll('source').forEach(s => {
                                if (s.src) sources.push(s.src);
                            });
                        });
                        // Check for video in iframes
                        document.querySelectorAll('iframe').forEach(iframe => {
                            if (iframe.src) sources.push(iframe.src);
                        });
                        return sources;
                    }
                """)

                await browser.close()

                if not video_sources:
                    return DownloadResult.failure(
                        error="No video sources found in DOM",
                        strategy=self.name,
                    )

                import httpx
                media_url = video_sources[0]
                output_path = output_dir / f"dom_video_{url.path.replace('/', '_')[-40:]}.mp4"

                async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
                    response = await client.get(media_url)
                    response.raise_for_status()
                    output_path.write_bytes(response.content)

                if output_path.exists() and output_path.stat().st_size > 0:
                    return DownloadResult.success(
                        file_path=output_path,
                        strategy=self.name,
                    )

                return DownloadResult.failure(
                    error="Downloaded file is empty",
                    strategy=self.name,
                )

        except ImportError:
            return DownloadResult.failure(
                error="Playwright not installed. Run: pip install playwright && playwright install chromium",
                strategy=self.name,
            )
        except Exception as exc:
            return DownloadResult.failure(
                error=f"DOM extraction error: {exc!s}",
                strategy=self.name,
            )