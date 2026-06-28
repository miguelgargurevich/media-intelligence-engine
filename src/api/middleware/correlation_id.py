"""Correlation ID middleware for request tracing."""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get the current request correlation ID."""
    return correlation_id_var.get()


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a correlation ID into each request.

    Uses an existing X-Correlation-ID header if present, otherwise
    generates a new UUID. Makes it available via get_correlation_id().
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            str(uuid.uuid4()),
        )
        correlation_id_var.set(correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id

        return response