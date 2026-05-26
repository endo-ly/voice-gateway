"""Tests for GetLatestTranscription use case."""

from app.application.use_cases.get_latest_transcription import GetLatestTranscription
from app.domain.value_objects.transcription_result import TranscriptionResult
from app.infrastructure.repositories.in_memory_transcription_store import InMemoryTranscriptionStore


def _make_result(**overrides):
    defaults = {
        "text": "hello",
        "language": "ja",
        "duration_sec": 5.0,
        "processing_ms": 100,
        "provider": "fake",
        "model": "test-model",
    }
    defaults.update(overrides)
    return TranscriptionResult(**defaults)


class TestGetLatestTranscription:
    def test_returns_none_when_empty(self):
        store = InMemoryTranscriptionStore()
        uc = GetLatestTranscription(store)
        assert uc.execute() is None

    def test_returns_latest(self):
        store = InMemoryTranscriptionStore()
        store.set_latest(_make_result(text="test"))
        uc = GetLatestTranscription(store)
        result = uc.execute()
        assert result is not None
        assert result.text == "test"
