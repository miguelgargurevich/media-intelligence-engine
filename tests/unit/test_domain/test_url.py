"""Tests for URL value object."""

import pytest

from src.domain.value_objects.url import URL


class TestURL:
    """Test suite for URL value object."""

    def test_create_valid_url(self) -> None:
        url = URL("https://www.youtube.com/watch?v=abc123")
        assert url.domain == "www.youtube.com"
        assert url.path == "/watch"
        assert isinstance(url.is_video_platform, bool)

    def test_url_without_scheme(self) -> None:
        url = URL.from_string("youtube.com/watch?v=123")
        assert url.value.startswith("https://")
        assert "youtube.com" in url.domain

    def test_invalid_url(self) -> None:
        with pytest.raises(ValueError):
            URL("not-a-url")

    def test_query_params(self) -> None:
        url = URL("https://example.com/page?key=value&num=42")
        params = url.query_params
        assert params["key"] == "value"
        assert params["num"] == "42"

    def test_video_platform_detection(self) -> None:
        youtube = URL("https://youtube.com/watch?v=test")
        assert youtube.is_video_platform

        tiktok = URL("https://tiktok.com/@user/video/123")
        assert tiktok.is_video_platform

        generic = URL("https://example.com/page")
        assert not generic.is_video_platform

    def test_str_representation(self) -> None:
        url = URL("https://example.com")
        assert str(url) == "https://example.com"
        assert repr(url) == "URL('https://example.com')"