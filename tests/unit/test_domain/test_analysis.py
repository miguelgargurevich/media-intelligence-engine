"""Tests for AnalysisResult entity."""

from src.domain.entities.analysis import AnalysisResult
from src.domain.value_objects.timestamp import TimelineEntry


class TestAnalysisResult:
    """Test suite for AnalysisResult entity."""

    def test_empty_result(self) -> None:
        result = AnalysisResult()
        assert result.status == "pending"
        assert not result.is_complete
        assert result.to_dict()["status"] == "pending"

    def test_completed_result(self) -> None:
        result = AnalysisResult(status="completed")
        assert result.is_complete
        assert not result.has_transcript
        assert not result.has_visual_data

    def test_with_transcript(self) -> None:
        result = AnalysisResult(transcript="Hello world", status="completed")
        assert result.has_transcript
        assert result.transcript == "Hello world"

    def test_with_timeline(self) -> None:
        entry = TimelineEntry(timestamp=10.5, text="sample")
        result = AnalysisResult(timeline=[entry], status="completed")
        assert result.has_visual_data
        assert len(result.timeline) == 1
        assert result.timeline[0].timestamp == 10.5

    def test_to_dict_structure(self) -> None:
        result = AnalysisResult(
            title="Test Video",
            description="A test",
            duration=120.0,
            language="es",
            source_url="https://example.com/video",
            status="completed",
        )
        d = result.to_dict()
        assert d["title"] == "Test Video"
        assert d["duration"] == 120.0
        assert d["language"] == "es"
        assert len(d["timeline"]) == 0
        assert d["commands"] == []