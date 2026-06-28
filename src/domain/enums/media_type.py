"""Media type enumerations."""

from enum import Enum


class MediaType(str, Enum):
    """Types of media content that can be analyzed."""

    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    LIVESTREAM = "livestream"
    UNKNOWN = "unknown"


class DownloadStrategy(str, Enum):
    """Available download strategies in priority order."""

    YT_DLP = "yt-dlp"
    GALLERY_DL = "gallery-dl"
    HTML_EXTRACTION = "html_extraction"
    DOM_INSPECTION = "dom_inspection"
    PLAYWRIGHT_DIRECT = "playwright_direct"
    SCREEN_RECORDING = "screen_recording"
    FALLBACK = "fallback"


class PipelineStatus(str, Enum):
    """Status of the analysis pipeline."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    RECORDING = "recording"
    EXTRACTING_FRAMES = "extracting_frames"
    EXTRACTING_AUDIO = "extracting_audio"
    RUNNING_OCR = "running_ocr"
    TRANSCRIBING = "transcribing"
    ANALYZING_VISION = "analyzing_vision"
    FUSING = "fusing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class VisionProviderType(str, Enum):
    """Supported vision AI providers."""

    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    QWEN = "qwen"
    OLLAMA = "ollama"


class StorageBackend(str, Enum):
    """Supported storage backends."""

    LOCAL = "local"
    S3 = "s3"