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

                # Intercept network requests to capture video/media URLs BEFORE navigation
                video_urls: list[str] = []

                async def intercept_response(response):
                    content_type = response.headers.get("content-type", "")
                    if any(t in content_type for t in ["video/", "audio/", "application/octet-stream"]):
                        url_str = str(response.url)
                        if url_str not in video_urls:
                            video_urls.append(url_str)

                page.on("response", intercept_response)

                await page.goto(str(url), wait_until="networkidle", timeout=30000)

                # Wait a bit more for dynamic content and video to load
                await asyncio.sleep(5)

                # Also check DOM for video elements
                dom_sources = await page.evaluate("""
                    () => {
                        const sources = [];
                        document.querySelectorAll('video').forEach(v => {
                            if (v.src && !v.src.startsWith('blob:')) sources.push(v.src);
                            v.querySelectorAll('source').forEach(s => {
                                if (s.src && !s.src.startsWith('blob:')) sources.push(s.src);
                            });
                        });
                        document.querySelectorAll('iframe').forEach(iframe => {
                            if (iframe.src) sources.push(iframe.src);
                        });
                        return sources;
                    }
                """)

                # Also try to extract from meta tags / JSON-LD
                meta_urls = await page.evaluate("""
                    () => {
                        const urls = [];
                        const metas = document.querySelectorAll('meta[property="og:video"], meta[name="twitter:player:stream"]');
                        metas.forEach(m => { if (m.content) urls.push(m.content); });
                        return urls;
                    }
                """)

                await browser.close()

                # Collect all candidate URLs (network captures + DOM + meta tags)
                all_candidates = video_urls + dom_sources + meta_urls

                if not all_candidates:
                    return DownloadResult.failure(
                        error="No video sources found in DOM or network traffic",
                        strategy=self.name,
                    )

                import httpx
                media_url = all_candidates[0]

                # Handle protocol-relative URLs
                if media_url.startswith("//"):
                    media_url = f"https:{media_url}"

                if not media_url.startswith(("http://", "https://")):
                    return DownloadResult.failure(
                        error=f"Invalid media URL format: {media_url[:100]}",
                        strategy=self.name,
                    )

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