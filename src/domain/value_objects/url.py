"""URL value object with validation."""

from dataclasses import dataclass
from urllib.parse import urlparse, ParseResult


@dataclass(frozen=True)
class URL:
    """Immutable URL value object with validation and parsing utilities."""

    value: str

    def __post_init__(self) -> None:
        """Validate URL on creation."""
        parsed = urlparse(self.value)
        if not parsed.scheme or not parsed.netloc:
            msg = f"Invalid URL: {self.value}"
            raise ValueError(msg)

    @classmethod
    def from_string(cls, url_str: str) -> "URL":
        """Create a URL from a string, adding https:// if missing."""
        if not url_str.startswith(("http://", "https://")):
            url_str = f"https://{url_str}"
        return cls(value=url_str)

    @property
    def parsed(self) -> ParseResult:
        """Return parsed URL components."""
        return urlparse(self.value)

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        return self.parsed.netloc.lower()

    @property
    def path(self) -> str:
        """Extract path from URL."""
        return self.parsed.path

    @property
    def query_params(self) -> dict[str, str]:
        """Extract query parameters from URL."""
        from urllib.parse import parse_qs

        params = parse_qs(self.parsed.query)
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    @property
    def is_video_platform(self) -> bool:
        """Check if URL belongs to a known video platform."""
        video_domains = {
            "youtube.com",
            "youtu.be",
            "tiktok.com",
            "instagram.com",
            "facebook.com",
            "twitch.tv",
            "vimeo.com",
            "dailymotion.com",
        }
        return any(d in self.domain for d in video_domains)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"URL('{self.value}')"