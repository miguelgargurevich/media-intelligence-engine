"""Plugin system interfaces for extensible media extraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from src.domain.value_objects.url import URL


class IPlugin(ABC):
    """Base interface for all plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        ...

    async def initialize(self) -> None:
        """Called when plugin is loaded. Override for setup."""
        ...

    async def shutdown(self) -> None:
        """Called when plugin is unloaded. Override for cleanup."""
        ...


class IExtractor(IPlugin, ABC):
    """Interface for content extractors that handle specific platforms.

    Each extractor knows how to handle a specific type of source
    (YouTube, TikTok, Instagram, etc.) and can extract content
    from it optimally.
    """

    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform name this extractor handles (e.g., 'youtube')."""
        ...

    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority order (lower = tried first)."""
        ...

    @abstractmethod
    def can_handle(self, url: URL) -> bool:
        """Check if this extractor can handle the given URL.

        Should check domain patterns and URL structure.
        """
        ...

    @abstractmethod
    async def extract(
        self,
        url: URL,
        output_dir: Path,
        **kwargs,
    ) -> dict[str, Any]:
        """Extract content from the given URL.

        Returns a dict with extracted data. At minimum should include
        whether extraction was successful and the file path.
        """
        ...


class PluginRegistry:
    """Central registry for all plugins.

    Plugins register themselves automatically. The registry
    resolves which extractor to use for a given URL.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, IPlugin] = {}
        self._extractors: list[IExtractor] = []

    def register(self, plugin: IPlugin) -> None:
        """Register a plugin in the system."""
        self._plugins[plugin.name] = plugin
        if isinstance(plugin, IExtractor):
            self._extractors.append(plugin)
            # Sort by priority (lower = first)
            self._extractors.sort(key=lambda e: e.priority)
            plugin_name = plugin.name
            _ = f"Extractor registered: {plugin_name}"

    def unregister(self, name: str) -> None:
        """Unregister a plugin by name."""
        if name in self._plugins:
            plugin = self._plugins.pop(name)
            if isinstance(plugin, IExtractor):
                self._extractors = [e for e in self._extractors if e.name != name]

    def get_plugin(self, name: str) -> Optional[IPlugin]:
        """Get a registered plugin by name."""
        return self._plugins.get(name)

    def get_extractor_for(self, url: URL) -> Optional[IExtractor]:
        """Find the best extractor for a given URL.

        Iterates extractors in priority order and returns
        the first one that can handle the URL.
        """
        for extractor in self._extractors:
            if extractor.can_handle(url):
                return extractor
        return None

    @property
    def plugins(self) -> dict[str, IPlugin]:
        """All registered plugins."""
        return dict(self._plugins)

    @property
    def extractors(self) -> list[IExtractor]:
        """All registered extractors."""
        return list(self._extractors)

    @property
    def count(self) -> int:
        """Total number of registered plugins."""
        return len(self._plugins)


# Global registry instance
registry = PluginRegistry()


def register_plugin(cls: type) -> type:
    """Decorator to auto-register a plugin class.

    Usage:
        @register_plugin
        class YouTubeExtractor(IExtractor):
            ...
    """
    instance = cls()
    registry.register(instance)
    return cls