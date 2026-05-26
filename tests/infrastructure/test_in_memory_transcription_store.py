"""Tests for InMemoryTranscriptionStore."""

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


class TestInMemoryTranscriptionStore:
    def test_initial_state_is_none(self):
        store = InMemoryTranscriptionStore()
        assert store.get_latest() is None

    def test_set_and_get(self):
        store = InMemoryTranscriptionStore()
        result = _make_result()
        store.set_latest(result)
        assert store.get_latest() is not None
        assert store.get_latest().text == "hello"

    def test_overwrite_latest(self):
        store = InMemoryTranscriptionStore()
        store.set_latest(_make_result(text="first"))
        store.set_latest(_make_result(text="second"))
        assert store.get_latest().text == "second"

    def test_timestamp_set(self):
        store = InMemoryTranscriptionStore()
        store.set_latest(_make_result())
        assert store.timestamp is not None
        assert "T" in store.timestamp or "Z" in store.timestamp
