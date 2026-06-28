# =============================================================================
# Dockerfile - Media Intelligence Engine
# =============================================================================

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev,vision]" 2>/dev/null || \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] pydantic pydantic-settings httpx \
        structlog tenacity python-multipart opencv-python-headless \
        yt-dlp gallery-dl
RUN pip install --no-cache-dir openai-whisper

COPY src/ ./src/

RUN mkdir -p /data/downloads /data/recordings /data/output /data/temp

RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --gid 1001 app && \
    chown -R app:app /data /app

USER app

EXPOSE 8000

ENTRYPOINT ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["--log-level", "info"]
