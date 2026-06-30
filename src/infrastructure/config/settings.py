"""Application settings using Pydantic Settings.

All configuration comes from environment variables (.env file).
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    workers: int = 4

    # --- Analysis ---
    default_fps: float = 1.0
    default_language: str = "es"
    max_frames: int = 500
    max_duration_seconds: int = 3600

    # --- Directories ---
    download_dir: Path = Path("/data/downloads")
    recording_dir: Path = Path("/data/recordings")
    output_dir: Path = Path("/data/output")
    temp_dir: Path = Path("/data/temp")

    # --- Downloaders ---
    yt_dlp_path: str = "yt-dlp"
    gallery_dl_path: str = "gallery-dl"
    ffmpeg_path: str = "ffmpeg"

    # --- Playwright ---
    playwright_headless: bool = True
    playwright_timeout_ms: int = 30000

    # --- Whisper ---
    whisper_model: str = "base"
    whisper_device: str = "cpu"

    # --- OCR ---
    ocr_device: str = "cpu"
    ocr_lang: str = "es,en"

    # --- Vision Providers ---
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    # base_url opcional para apuntar el proveedor "openai" a un endpoint OpenAI-compatible
    # (ej. DeepInfra: https://api.deepinfra.com/v1/openai con un modelo VL como Qwen3-VL).
    openai_base_url: Optional[str] = None

    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"

    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-vl2"

    qwen_api_key: Optional[str] = None
    qwen_model: str = "qwen-vl-max"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2-vision"

    default_vision_provider: str = "openai"

    # --- Semantic Analysis (LLM cascada) ---
    # DeepInfra (OpenAI-compatible) primario barato; DeepSeek/Gemini/Groq de fallback.
    deepinfra_llm_api_key: Optional[str] = None
    deepinfra_llm_model: str = "deepseek-ai/DeepSeek-V4-Flash"
    deepseek_llm_api_key: Optional[str] = None
    deepseek_llm_model: str = "deepseek-chat"

    groq_api_key: Optional[str] = None
    groq_llm_model: str = "llama-3.3-70b-versatile"
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # Transcription provider: "auto" (Groq if key present, else local), "groq", "local"
    transcription_provider: str = "auto"

    semantic_timeout_seconds: int = 300  # 5 min por proveedor

    # --- Puente de descarga residencial (Instagram) ---
    # IG bloquea la IP del datacenter; un daemon en una máquina residencial (Mac) baja
    # los reels encolados y los sube a /analyze-file. mie guarda el análisis en dashboardIA
    # y avisa por Telegram (el MCP no está en el loop en este flujo).
    ig_bridge_enabled: bool = True
    dashboard_api_base: Optional[str] = None       # ej. https://dashboardia.gargurevich.dev
    dashboard_service_token: Optional[str] = None  # X-Service-Token (= AGENT_SERVICE_TOKEN del backend)
    telegram_bot_token: Optional[str] = None       # mismo token del bot de OpenClaw
    telegram_notify_chat_id: Optional[str] = None  # chat de Miguel

    # --- Storage ---
    storage_backend: str = "local"
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_bucket: Optional[str] = None

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # --- OpenTelemetry ---
    otel_service_name: str = "media-intelligence-engine"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4318"
    otel_traces_sampler: str = "always_on"


# Global settings instance
settings = Settings()