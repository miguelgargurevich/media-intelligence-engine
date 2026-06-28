"""FastAPI application setup."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.correlation_id import CorrelationIDMiddleware
from src.api.routers import analyze, health
from src.infrastructure.config.logging_config import configure_logging, get_logger
from src.infrastructure.config.settings import settings

# Configure structured logging
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Media Intelligence Engine",
    description="Microservicio para análisis automático de contenido multimedia.\n\n"
    "Extrae conocimiento estructurado de cualquier contenido multimedia a partir de una URL.\n\n"
    "**Pipeline:**\n"
    "1. Descarga multiesrategia (yt-dlp, HTML, DOM)\n"
    "2. Grabación de pantalla (fallback)\n"
    "3. Extracción de frames\n"
    "4. OCR (PaddleOCR)\n"
    "5. Transcripción (Whisper)\n"
    "6. Análisis con visión AI (GPT, Gemini, Claude)\n"
    "7. Fusión de resultados en documento estructurado",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIDMiddleware)

# Routers
app.include_router(health.router)
app.include_router(analyze.router)


@app.on_event("startup")
async def startup_event() -> None:
    """Actions to run on application startup."""
    # Ensure required directories exist
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    settings.recording_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    # Initialize plugin system
    from src.ports.plugin import registry
    from src.infrastructure.plugins import youtube_extractor  # noqa: F401
    from src.infrastructure.plugins import instagram_extractor  # noqa: F401

    logger.info(
        "Application started",
        plugins_count=registry.count,
        extractors_count=len(registry.extractors),
        host=settings.host,
        port=settings.port,
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Actions to run on application shutdown."""
    logger.info("Application shutting down")