"""Groq Whisper speech-to-text implementation.

Cloud transcription via Groq's `whisper-large-v3-turbo` — the same engine the
dashboard meetings pipeline uses. Faster and higher quality than local Whisper,
at the cost of a 25 MB upload limit (callers should send compressed audio).
"""

from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.infrastructure.config.logging_config import get_logger
from src.ports.speech_to_text import ISpeechToText, TranscriptionResult, TranscriptionSegment

logger = get_logger(__name__)

# Groq validates the format by the multipart filename extension.
# Accepted: flac mp3 mp4 mpeg mpga m4a ogg opus wav webm
_EXT_TO_MIME = {
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
    "wav": "audio/wav",
    "webm": "audio/webm",
    "flac": "audio/flac",
    "mpeg": "audio/mpeg",
    "mpga": "audio/mpeg",
}
_SUPPORTED = set(_EXT_TO_MIME.keys())

# Groq hard limit on upload size.
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _part_meta(audio_path: Path) -> tuple[str, str]:
    """Return (filename, content_type) Groq will accept, derived from extension."""
    ext = audio_path.suffix.lstrip(".").lower()
    if ext not in _SUPPORTED:
        ext = "webm"
    return f"audio.{ext}", _EXT_TO_MIME[ext]


class GroqWhisperSTT(ISpeechToText):
    """Speech-to-text using Groq's hosted Whisper (whisper-large-v3-turbo)."""

    @property
    def name(self) -> str:
        return "groq-whisper"

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model: str = "base",  # ignored; Groq model comes from settings
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe an audio file via the Groq Whisper API."""
        if not settings.groq_api_key:
            return TranscriptionResult.failure(error="GROQ_API_KEY not configured")

        if not audio_path.exists():
            return TranscriptionResult.failure(error=f"Audio file not found: {audio_path}")

        size = audio_path.stat().st_size
        if size > _MAX_UPLOAD_BYTES:
            return TranscriptionResult.failure(
                error=f"Audio file {size / 1e6:.1f}MB exceeds Groq 25MB limit",
            )

        filename, content_type = _part_meta(audio_path)

        data = {
            "model": settings.groq_whisper_model,
            "response_format": "verbose_json",
            "temperature": "0",
        }
        lang = language or settings.default_language
        if lang:
            data["language"] = lang

        try:
            import httpx

            with audio_path.open("rb") as fh:
                files = {"file": (filename, fh, content_type)}
                async with httpx.AsyncClient(timeout=settings.semantic_timeout_seconds) as client:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                        data=data,
                        files=files,
                    )

            if not resp.is_success:
                return TranscriptionResult.failure(
                    error=f"Groq Whisper error {resp.status_code}: {resp.text[:300]}",
                )

            payload = resp.json()
            text = (payload.get("text") or "").strip()

            segments: list[TranscriptionSegment] = []
            for seg in payload.get("segments", []) or []:
                segments.append(
                    TranscriptionSegment(
                        text=(seg.get("text") or "").strip(),
                        start=seg.get("start", 0.0),
                        end=seg.get("end", 0.0),
                        confidence=1.0,
                    )
                )

            if not text and not segments:
                return TranscriptionResult.failure(error="Groq Whisper returned empty result")

            logger.info("Groq Whisper transcription succeeded", segments=len(segments))
            return TranscriptionResult.success(
                text=text,
                segments=segments,
                language=payload.get("language", lang),
                duration=payload.get("duration"),
            )

        except ImportError:
            return TranscriptionResult.failure(error="httpx not installed")
        except Exception as exc:
            return TranscriptionResult.failure(error=f"Groq Whisper error: {exc!s}")
