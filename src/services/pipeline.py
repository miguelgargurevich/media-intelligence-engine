"""Pipeline orchestrator - coordinates the entire analysis workflow."""

import asyncio
from pathlib import Path
from typing import Optional

from src.domain.entities.analysis import AnalysisResult
from src.domain.entities.media import Media, FrameCollection, AudioTrack
from src.domain.enums.media_type import MediaType, PipelineStatus, DownloadStrategy
from src.domain.value_objects.url import URL
from src.domain.value_objects.timestamp import TimelineEntry
from src.infrastructure.config.settings import settings
from src.infrastructure.config.logging_config import get_logger
from src.infrastructure.downloaders.yt_dlp_downloader import YTDLPDownloader
from src.infrastructure.downloaders.gallery_dl_downloader import GalleryDLDownloader
from src.infrastructure.downloaders.html_extractor import HTMLExtractorDownloader
from src.infrastructure.downloaders.dom_extractor import DOMExtractorDownloader
from src.infrastructure.recorder.ffmpeg_recorder import FFmpegScreenRecorder
from src.infrastructure.ocr.paddle_ocr_engine import PaddleOCREngine
from src.infrastructure.speech.whisper_stt import WhisperSTT
from src.infrastructure.speech.groq_whisper_stt import GroqWhisperSTT
from src.infrastructure.storage.local_storage import LocalStorage
from src.infrastructure.vision.gpt_vision import GPTVisionProvider
from src.services.semantic_analyzer import enrich_semantics
from src.ports.downloader import IDownloader, DownloadResult

logger = get_logger(__name__)


class Pipeline:
    """Main analysis pipeline that orchestrates the entire workflow."""

    def __init__(self) -> None:
        self.downloaders: list[IDownloader] = [
            YTDLPDownloader(),
            GalleryDLDownloader(),
            HTMLExtractorDownloader(),
            DOMExtractorDownloader(),
        ]
        self.recorder = FFmpegScreenRecorder()
        self.ocr = PaddleOCREngine()
        self.stt = WhisperSTT()          # local fallback
        self.groq_stt = GroqWhisperSTT()  # cloud primary (same engine as meetings)
        self.vision = GPTVisionProvider()
        self.storage = LocalStorage()

    async def run(self, url_str: str, **kwargs) -> AnalysisResult:
        """Execute the complete analysis pipeline for a given URL.

        Args:
            url_str: The URL to analyze.
            **kwargs: Override settings (fps, language, vision_provider, etc.).

        Returns:
            AnalysisResult with all extracted knowledge.
        """
        result = AnalysisResult(source_url=url_str)
        url = URL.from_string(url_str)

        try:
            # Phase 1: Download media
            result.status = PipelineStatus.DOWNLOADING.value
            media = await self._download_media(url, result)
            if not media or not media.file_path:
                # Phase 2: Try recording as fallback
                result.status = PipelineStatus.RECORDING.value
                media = await self._record_media(url, result)
                if not media or not media.file_path:
                    result.status = PipelineStatus.FAILED.value
                    result.error = "Could not obtain media from URL"
                    return result

            result.title = media.title
            result.description = media.description
            result.duration = media.duration
            result.language = media.language or settings.default_language

            # Phase 3: Extract frames
            result.status = PipelineStatus.EXTRACTING_FRAMES.value
            fps = kwargs.get("fps", settings.default_fps)
            frames = await self._extract_frames(media, fps=fps)

            # Phase 4: OCR on frames
            result.status = PipelineStatus.RUNNING_OCR.value
            await self._run_ocr_on_frames(frames)

            # Phase 5: Extract and transcribe audio
            result.status = PipelineStatus.EXTRACTING_AUDIO.value
            if media.file_path:
                audio = await self._extract_audio(media)
                if audio:
                    result.status = PipelineStatus.TRANSCRIBING.value
                    transcription = await self._transcribe_audio(audio, language=media.language)
                    result.transcript = transcription.text
                    result.transcript_segments = [s.to_dict() for s in transcription.segments]

            # Phase 6: Vision analysis on key frames
            result.status = PipelineStatus.ANALYZING_VISION.value
            await self._analyze_frames_vision(frames)

            # Phase 7: Fuse all results
            result.status = PipelineStatus.FUSING.value
            result = await self._fuse_results(result, media, frames)

            # Phase 8: Semantic enrichment (LLM cascade: DeepSeek → Gemini → Groq)
            if result.transcript:
                logger.info("Starting semantic enrichment (LLM cascade)...")
                try:
                    timeline_dicts = [
                        {
                            "timestamp": entry.timestamp,
                            "text": entry.text,
                            "ocr_text": entry.ocr_text,
                            "vision_description": entry.vision_description,
                        }
                        for entry in result.timeline
                    ]
                    semantics = await enrich_semantics(
                        transcript=result.transcript,
                        title=result.title or "",
                        timeline=timeline_dicts,
                    )
                    # Map semantic fields to result
                    # Use LLM-generated title when the source had no metadata title
                    # (e.g. Instagram reels): avoids generic "MIE Analysis" downstream.
                    if not result.title and semantics.get("title"):
                        result.title = semantics["title"]
                    result.sentiment = semantics.get("sentiment")
                    result.topic_type = semantics.get("topicType")
                    result.chapters = semantics.get("chapters", [])
                    result.highlights = semantics.get("highlights", [])
                    result.participants = semantics.get("participants", [])
                    result.tasks = semantics.get("tasks", [])
                    result.agreements = semantics.get("agreements", [])
                    result.risks = semantics.get("risks", [])
                    result.open_questions = semantics.get("openQuestions", [])
                    result.next_steps = semantics.get("nextSteps", [])
                    result.hashtags = semantics.get("hashtags", [])
                    result.follow_up_email = semantics.get("followUpEmail")
                    result.diagrams = semantics.get("diagrams", [])
                    # Keywords from LLM cuando la extracción (OCR) no encontró ninguno
                    llm_keywords = semantics.get("keywords")
                    if llm_keywords and not result.keywords:
                        result.keywords = llm_keywords
                    # Override/extend summaries with LLM-generated ones
                    if semantics.get("markdown"):
                        result.markdown = semantics["markdown"]
                    if semantics.get("html"):
                        result.html = semantics["html"]
                    # Summary ejecutivo del LLM (lista de puntos) reemplaza el fallback básico
                    llm_summary = semantics.get("summary")
                    if isinstance(llm_summary, list) and llm_summary:
                        result.summary = "\n".join(f"- {s}" for s in llm_summary if s)
                    elif isinstance(llm_summary, str) and llm_summary.strip():
                        result.summary = llm_summary.strip()
                    # Derivar título del H1 del markdown si el extractor no entregó uno (ej: reels)
                    if not result.title:
                        result.title = self._derive_title(result)
                    logger.info("Semantic enrichment completed")
                except Exception as exc:
                    logger.warning("Semantic enrichment failed", error=str(exc))

            result.status = PipelineStatus.COMPLETED.value

        except Exception as exc:
            logger.error("Pipeline failed", error=str(exc))
            result.status = PipelineStatus.FAILED.value
            result.error = str(exc)

        return result

    async def _download_media(self, url: URL, result: AnalysisResult) -> Optional[Media]:
        """Try each downloader in sequence until one succeeds."""
        for downloader in self.downloaders:
            try:
                dl_result: DownloadResult = await downloader.download(
                    url,
                    settings.download_dir,
                )
                if dl_result.success and dl_result.file_path:
                    media = Media(
                        source_url=url,
                        media_type=MediaType.VIDEO,
                        file_path=dl_result.file_path,
                        title=dl_result.title,
                        duration=dl_result.duration,
                        width=dl_result.width,
                        height=dl_result.height,
                    )
                    logger.info("Media downloaded", strategy=downloader.name, path=str(dl_result.file_path))
                    return media
                logger.warning("Downloader failed", strategy=downloader.name, error=dl_result.error)
            except Exception as exc:
                logger.warning("Downloader error", strategy=downloader.name, error=str(exc))
                continue
        return None

    async def _record_media(self, url: URL, result: AnalysisResult) -> Optional[Media]:
        """Fallback: record screen while playing media."""
        output_path = settings.recording_dir / f"recording_{url.path.replace('/', '_')[-40:]}.mp4"
        recording = await self.recorder.record(
            url=str(url),
            output_path=output_path,
            duration=settings.max_duration_seconds,
        )
        if recording.success and recording.file_path:
            return Media(
                source_url=url,
                media_type=MediaType.VIDEO,
                file_path=recording.file_path,
                duration=recording.duration,
            )
        return None

    async def _extract_frames(self, media: Media, fps: float = 1.0) -> FrameCollection:
        """Extract frames from video using OpenCV."""
        import cv2

        fps = fps or 1.0  # Ensure fps is not None
        collection = FrameCollection(fps=fps, source_duration=media.duration or 0)
        if not media.file_path:
            return collection

        cap = cv2.VideoCapture(str(media.file_path))
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # Default if cannot detect
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(video_fps / fps))

        frame_idx = 0
        saved_idx = 0
        frames_dir = settings.temp_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / video_fps
                frame_path = frames_dir / f"frame_{saved_idx:06d}.jpg"
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                from src.domain.entities.media import Frame
                collection.add_frame(
                    Frame(
                        index=saved_idx,
                        timestamp=timestamp,
                        file_path=frame_path,
                        width=frame.shape[1],
                        height=frame.shape[0],
                    )
                )
                saved_idx += 1

                if saved_idx >= settings.max_frames:
                    break

            frame_idx += 1

        cap.release()
        logger.info("Frames extracted", count=collection.total_frames)
        return collection

    async def _run_ocr_on_frames(self, frames: FrameCollection) -> None:
        """Run OCR on all extracted frames."""
        for frame in frames.frames:
            ocr_result = await self.ocr.extract_text(
                frame.file_path,
                language=settings.default_language,
            )
            if ocr_result.success:
                frame.ocr_text = ocr_result.full_text

    async def _extract_audio(self, media: Media) -> Optional[AudioTrack]:
        """Extract audio from video using FFmpeg."""
        import subprocess
        import json

        if not media.file_path:
            return None

        # Compressed mp3 mono 16kHz: small enough for the Groq 25MB upload limit
        # (~0.48 MB/min → ~50 min) and read fine by local Whisper as fallback.
        audio_path = settings.temp_dir / f"audio_{media.file_path.stem}.mp3"

        cmd = [
            settings.ffmpeg_path,
            "-i", str(media.file_path),
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-b:a", "64k",  # 64 kbps — ample for speech
            "-ar", "16000",  # 16kHz sample rate
            "-ac", "1",  # Mono
            "-y",
            str(audio_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

        if audio_path.exists():
            duration = media.duration or 0
            return AudioTrack(
                file_path=audio_path,
                duration=duration,
                sample_rate=16000,
                channels=1,
                format="mp3",
            )
        return None

    async def _transcribe_audio(self, audio: AudioTrack, language: Optional[str] = None) -> "TranscriptionResult":
        """Transcribe audio with Groq Whisper (cloud) primary, local Whisper fallback.

        Provider selection via settings.transcription_provider:
          - "auto"  : Groq if GROQ_API_KEY set, else local; falls back to local on Groq failure
          - "groq"  : Groq only (no fallback)
          - "local" : local Whisper only
        """
        lang = language or settings.default_language
        provider = (settings.transcription_provider or "auto").lower()

        use_groq = provider in ("auto", "groq") and bool(settings.groq_api_key)
        if use_groq:
            logger.info("Transcribing via Groq Whisper", model=settings.groq_whisper_model)
            result = await self.groq_stt.transcribe(audio.file_path, language=lang)
            if result.success:
                return result
            logger.warning("Groq Whisper failed", error=result.error)
            if provider == "groq":
                return result  # explicit groq-only: no fallback

        logger.info("Transcribing via local Whisper", model=settings.whisper_model)
        return await self.stt.transcribe(
            audio.file_path,
            language=lang,
            model=settings.whisper_model,
        )

    async def _analyze_frames_vision(self, frames: FrameCollection) -> None:
        """Run vision analysis on key frames with fallback providers."""
        key_frames = frames.key_frames
        if not key_frames:
            return

        # Try providers in order until one succeeds
        vision_providers = await self._get_vision_providers()
        last_analysis = None

        for provider in vision_providers:
            logger.info("Running vision analysis", provider=provider.provider_name)
            analyses = await provider.analyze_images_batch(
                [f.file_path for f in key_frames],
            )
            # Check if all analyses succeeded
            if all(a.success for a in analyses):
                for frame, analysis in zip(key_frames, analyses):
                    if analysis.success:
                        frame.vision_description = analysis.description
                logger.info("Vision analysis completed", provider=provider.provider_name)
                return

            # Log failure and try next
            failed_count = sum(1 for a in analyses if not a.success)
            logger.warning(
                "Vision provider failed",
                provider=provider.provider_name,
                failed=failed_count,
            )
            last_analysis = analyses

        # All providers failed, log the last error
        if last_analysis:
            logger.error(
                "All vision providers failed",
                last_error=last_analysis[0].error if last_analysis else "unknown",
            )

    async def _get_vision_providers(self) -> list:
        """Get list of vision providers based on configured API keys."""
        from src.infrastructure.vision.gpt_vision import GPTVisionProvider
        from src.infrastructure.vision.gemini_vision import GeminiVisionProvider
        from src.infrastructure.vision.qwen_vision import QwenVisionProvider
        from src.infrastructure.vision.deepseek_vision import DeepSeekVisionProvider

        providers = []

        # Always add the default first
        if settings.default_vision_provider == "openai" and settings.openai_api_key:
            providers.append(GPTVisionProvider())
        elif settings.default_vision_provider == "gemini" and settings.gemini_api_key:
            providers.append(GeminiVisionProvider())

        # Add fallbacks in order
        if settings.openai_api_key and not any(p.provider_name == "openai" for p in providers):
            providers.append(GPTVisionProvider())
        if settings.gemini_api_key and not any(p.provider_name == "gemini" for p in providers):
            providers.append(GeminiVisionProvider())
        if settings.deepseek_api_key:
            providers.append(DeepSeekVisionProvider())
        if settings.qwen_api_key:
            providers.append(QwenVisionProvider())

        if not providers:
            logger.warning("No vision providers configured")
            # Add a stub that always fails gracefully
            from src.infrastructure.vision.gpt_vision import GPTVisionProvider
            providers.append(GPTVisionProvider())

        return providers

    async def _fuse_results(
        self,
        result: AnalysisResult,
        media: Media,
        frames: FrameCollection,
    ) -> AnalysisResult:
        """Merge all extracted data into structured result."""
        all_commands: list[str] = []
        all_code_blocks: list[dict] = []
        all_urls: list[str] = []
        all_technologies: list[str] = []
        all_keywords: list[str] = []

        for frame in frames.frames:
            entry = TimelineEntry(
                timestamp=frame.timestamp,
                ocr_text=frame.ocr_text,
                vision_description=frame.vision_description,
            )

            # Extract items from OCR text
            if frame.ocr_text:
                lines = frame.ocr_text.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # Detect commands
                    if any(line.startswith(c) for c in ["$ ", "npm ", "pip ", "git ", "docker ", "kubectl ", "ssh ", "curl "]):
                        if line not in all_commands:
                            all_commands.append(line)
                            entry.commands.append(line)
                    # Detect URLs
                    import re
                    url_matches = re.findall(r'https?://[^\s]+', line)
                    for u in url_matches:
                        if u not in all_urls:
                            all_urls.append(u)
                            entry.urls.append(u)
                    # Detect code-like patterns
                    if re.search(r'(def\s+\w+\s*\(|class\s+\w+|import\s+\w+|const\s+\w+\s*=|function\s+\w+)', line):
                        code_entry = {"code": line, "language": None, "source": "ocr"}
                        if code_entry not in all_code_blocks:
                            all_code_blocks.append(code_entry)
                            entry.code_blocks.append(line)

            # Extract items from vision description
            if frame.vision_description:
                tech_keywords = [
                    "python", "javascript", "typescript", "react", "vue", "angular",
                    "docker", "kubernetes", "aws", "gcp", "azure", "node", "go",
                    "rust", "sql", "nosql", "redis", "postgresql", "mongodb",
                ]
                desc_lower = frame.vision_description.lower()
                for tech in tech_keywords:
                    if tech in desc_lower and tech not in all_technologies:
                        all_technologies.append(tech)
                        entry.technologies.append(tech)

            result.timeline.append(entry)

        result.commands = all_commands
        result.code_blocks = all_code_blocks
        result.urls = all_urls
        result.technologies = all_technologies
        result.keywords = all_keywords

        # Generate markdown summary
        result.markdown = self._generate_markdown(result)
        result.html = self._generate_html(result)
        result.summary = self._generate_summary(result)
        result.visual_summary = self._generate_visual_summary(frames)

        return result

    def _generate_markdown(self, result: AnalysisResult) -> str:
        """Generate a markdown document from analysis results."""
        md = []
        md.append(f"# {result.title or 'Media Analysis'}")
        md.append("")
        if result.description:
            md.append(f"_{result.description}_")
            md.append("")
        md.append(f"- **Duration:** {result.duration:.1f}s" if result.duration else "")
        md.append(f"- **Language:** {result.language}" if result.language else "")
        md.append("")

        if result.transcript:
            md.append("## Transcript")
            md.append("")
            md.append(result.transcript)
            md.append("")

        if result.commands:
            md.append("## Commands")
            md.append("")
            md.append("```bash")
            for cmd in result.commands:
                md.append(cmd)
            md.append("```")
            md.append("")

        if result.code_blocks:
            md.append("## Code Blocks")
            for block in result.code_blocks:
                md.append("")
                md.append(f"```{block.get('language', '')}")
                md.append(block.get("code", ""))
                md.append("```")

        if result.urls:
            md.append("## URLs")
            for u in result.urls:
                md.append(f"- {u}")

        if result.technologies:
            md.append("## Technologies")
            for tech in result.technologies:
                md.append(f"- {tech}")

        return "\n".join(md)

    def _generate_html(self, result: AnalysisResult) -> str:
        """Generate a simple HTML document from analysis results."""
        html = ["<!DOCTYPE html><html><head><meta charset='utf-8'>"]
        html.append(f"<title>{result.title or 'Media Analysis'}</title>")
        html.append("<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px}")
        html.append("h1{color:#333}.section{margin:20px 0}pre{background:#f4f4f4;padding:10px;border-radius:5px}")
        html.append("</style></head><body>")
        html.append(f"<h1>{result.title or 'Media Analysis'}</h1>")
        if result.description:
            html.append(f"<p><em>{result.description}</em></p>")
        if result.transcript:
            html.append("<div class='section'><h2>Transcript</h2>")
            html.append(f"<p>{result.transcript}</p></div>")
        if result.commands:
            html.append("<div class='section'><h2>Commands</h2><pre>")
            html.append("\n".join(f"{c}" for c in result.commands))
            html.append("</pre></div>")
        if result.urls:
            html.append("<div class='section'><h2>URLs</h2><ul>")
            for u in result.urls:
                html.append(f"<li><a href='{u}'>{u}</a></li>")
            html.append("</ul></div>")
        html.append("</body></html>")
        return "\n".join(html)

    def _derive_title(self, result: AnalysisResult) -> str:
        """Derive a title when the source provided none (e.g. Instagram reels).

        Prioriza el primer encabezado H1 del markdown del LLM; si no hay,
        usa el título del primer capítulo.
        """
        for line in (result.markdown or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        if result.chapters:
            first = result.chapters[0]
            if isinstance(first, dict) and first.get("title"):
                return str(first["title"]).strip()
        return ""

    def _generate_summary(self, result: AnalysisResult) -> str:
        """Generate a text summary."""
        parts = []
        if result.title:
            parts.append(f"Análisis de: {result.title}")
        if result.commands:
            parts.append(f"Se detectaron {len(result.commands)} comandos.")
        if result.code_blocks:
            parts.append(f"Se extrajeron {len(result.code_blocks)} bloques de código.")
        if result.urls:
            parts.append(f"Se encontraron {len(result.urls)} URLs.")
        if result.technologies:
            parts.append(f"Tecnologías identificadas: {', '.join(result.technologies)}.")
        if result.transcript:
            parts.append("Transcripción de audio disponible.")
        return " ".join(parts) if parts else "No se pudo generar resumen."

    def _generate_visual_summary(self, frames: FrameCollection) -> str:
        """Generate a visual summary from key frame descriptions."""
        descriptions = []
        for f in frames.frames[:5]:  # First 5 key frames
            if f.vision_description:
                descriptions.append(f"[{f.timestamp:.1f}s] {f.vision_description[:200]}")
        return "\n".join(descriptions) if descriptions else ""