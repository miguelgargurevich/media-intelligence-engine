"""Entry point for running the application directly."""

import uvicorn

from src.infrastructure.config.settings import settings


def main() -> None:
    """Run the application server."""
    uvicorn.run(
        "src.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
        workers=settings.workers,
    )


if __name__ == "__main__":
    main()