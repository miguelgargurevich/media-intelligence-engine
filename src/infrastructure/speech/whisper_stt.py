"""Whisper speech-to-text implementation."""

from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.speech_to_text import ISpeechToText, TranscriptionResult, TranscriptionSegment


class WhisperSTT(ISpeechToText):
    """Speech-to-text using OpenAI Whisper model."""

    def __init__(self) -> None:
        self._model = None

    async def _get_model(self, model_name: str):
        """Lazy-load Whisper model."""
        if self._model is None:
            import whisper

            self._model = whisper.load_model(
                model_name or settings.whisper_model,
                device=settings.whisper_device,
            )
        return self._model

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model: str = "base",
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio file using Whisper."""
        try:
            whisper_model = await self._get_model(model)

            # Run transcription in thread pool to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                None,
                lambda: whisper_model.transcribe(
                    str(audio_path),
                    language=language or settings.default_language,
                    task="transcribe",
                    verbose=False,
                ),
            )

            if not result or "text" not in result:
                return TranscriptionResult.failure(
                    error="Whisper returned empty result",
                )

            segments: list[TranscriptionSegment] = []
            if "segments" in result:
                for seg in result["segments"]:
                    segments.append(
                        TranscriptionSegment(
                            text=seg.get("text", ""),
                            start=seg.get("start", 0.0),
                            end=seg.get("end", 0.0),
                            confidence=seg.get("confidence", 1.0),
                        )
                    )

            return TranscriptionResult.success(
                text=result["text"].strip(),
                segments=segments,
                language=result.get("language", language),
                duration=result.get("duration", None),
            )

        except ImportError:
            return TranscriptionResult.failure(
                error="Whisper not installed. Run: pip install openai-whisper",
            )
        except Exception as exc:
            return TranscriptionResult.failure(
                error=f"Whisper transcription error: {exc!s}",
            )