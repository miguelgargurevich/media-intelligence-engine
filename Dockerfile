# =============================================================================
# Dockerfile - Media Intelligence Engine
# =============================================================================

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        ffmpeg \
        curl \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libdbus-1-3 libexpat1 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libpango-1.0-0 libcairo2 \
        2>/dev/null && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev,vision]" || \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] pydantic pydantic-settings httpx \
        structlog tenacity python-multipart playwright \
        openai google-generativeai anthropic ollama \
        yt-dlp gallery-dl

# Install Playwright browsers (for DOM extraction fallback) - run as root before USER app
ENV PLAYWRIGHT_BROWSERS_PATH=/app/playwright-browsers
RUN mkdir -p /app/playwright-browsers && \
    playwright install chromium 2>&1 || echo "Playwright install failed, will try at runtime"

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
