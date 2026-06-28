"""Health check endpoint."""

from fastapi import APIRouter

from src.api.schemas.responses import HealthResponse
from src.infrastructure.config.settings import settings

router = APIRouter(tags=["monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns the service health status, version, and service name.",
)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring and orchestration."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        service="media-intelligence-engine",
    )


@router.get(
    "/metrics",
    summary="Prometheus metrics endpoint",
    description="Exposes Prometheus-formatted metrics (placeholder).",
)
async def metrics() -> dict:
    """Placeholder metrics endpoint."""
    return {"metrics": "Prometheus metrics not yet implemented"}