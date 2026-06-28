# =============================================================================
# Dockerfile - Media Intelligence Engine
# =============================================================================

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies (separate update from install for better error handling)
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        ffmpeg \
        curl \
        2>/dev/null && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev,vision]" || \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] pydantic pydantic-settings httpx \
        structlog tenacity python-multipart \
        openai google-generativeai anthropic ollama \
        yt-dlp gallery-dl

# Install yt-dlp and gallery-dl (required for video downloads)
RUN pip install --no-cache-dir yt-dlp gallery-dl

# Copy application code
COPY src/ ./src/

# Create data directories
RUN mkdir -p /data/downloads /data/recordings /data/output /data/temp

# Create non-root user
RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --gid 1001 app && \
    chown -R app:app /data /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["--log-level", "info"]
