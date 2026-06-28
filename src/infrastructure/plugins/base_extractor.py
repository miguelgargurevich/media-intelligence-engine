"""Base extractor with common functionality for all platform extractors."""

from abc import ABC
from pathlib import Path
from typing import Any, Optional

from src.domain.value_objects.url import URL
from src.ports.plugin import IExtractor


class BaseExtractor(IExtractor, ABC):
    """Base class for platform-specific extractors."""

    @property
    def name(self) -> str:
        return f"{self.platform}_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return f"Extractor for {self.platform}"