"""Tests for TranscribeAudio use case."""

import pytest

from app.application.services.model_resolver import ModelResolver
from app.application.services.stt_profile_resolver import STTProfileResolver
from app.application.services.stt_provider_registry import STTProviderRegistry
from app.application.use_cases.transcribe_audio import TranscribeAudio
from app.domain.entities.model_profile import ModelProfile
from app.domain.errors import ProviderNotFoundError
from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult
from app.infrastructure.repositories.in_memory_transcription_store import InMemoryTranscriptionStore


def _make_stt_model(**overrides):
    defaults = {
        "id": "stt-default",
        "display_name": "STT Default",
        "direction": "stt",
        "provider": "fake_stt",
        "engine": "k2",
        "defaults": {"language": "ja", "max_audio_seconds": 30, "timeout_sec": 120},
        "provider_config": {},
    }
    defaults.update(overrides)
    return ModelProfile.model_validate(defaults)


class FakeModelRepo:
    def __init__(self, models=None):
        self._models = {m.id: m for m in (models or [])}

    def get_by_id(self, model_id):
        if model_id not in self._models:
            from app.domain.errors import ModelNotFoundError
            raise ModelNotFoundError(model_id)
        return self._models[model_id]

    def list_all(self):
        return list(self._models.values())


class FakeSTTProvider:
    provider_name = "fake_stt"

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        return TranscriptionResult(
            text="fake transcription",
            language=request.language,
            duration_sec=1.0,
            processing_ms=100,
            provider=self.provider_name,
            model=request.model_id,
        )

    def is_loaded(self):
        return True

    def capabilities(self):
        return {}


class TestTranscribeAudio:
    async def test_execute_returns_result(self, tmp_path):
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"\x00")

        model = _make_stt_model()
        repo = FakeModelRepo([model])
        registry = STTProviderRegistry()
        registry.register(FakeSTTProvider())
        store = InMemoryTranscriptionStore()

        uc = TranscribeAudio(
            profile_resolver=STTProfileResolver(ModelResolver(repo)),
            provider_registry=registry,
            transcription_store=store,
        )
        result = await uc.execute(model_id="stt-default", audio_path=str(wav))
        assert result.text == "fake transcription"
        assert result.source == "unknown"
        assert result.processing_ms >= 0

    async def test_execute_stores_result(self, tmp_path):
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"\x00")

        model = _make_stt_model()
        repo = FakeModelRepo([model])
        registry = STTProviderRegistry()
        registry.register(FakeSTTProvider())
        store = InMemoryTranscriptionStore()

        uc = TranscribeAudio(
            profile_resolver=STTProfileResolver(ModelResolver(repo)),
            provider_registry=registry,
            transcription_store=store,
        )
        await uc.execute(model_id="stt-default", audio_path=str(wav), source="test")
        assert store.get_latest() is not None
        assert store.get_latest()[0].source == "test"

    async def test_execute_without_store(self, tmp_path):
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"\x00")

        model = _make_stt_model()
        repo = FakeModelRepo([model])
        registry = STTProviderRegistry()
        registry.register(FakeSTTProvider())

        uc = TranscribeAudio(
            profile_resolver=STTProfileResolver(ModelResolver(repo)),
            provider_registry=registry,
        )
        result = await uc.execute(model_id="stt-default", audio_path=str(wav))
        assert result.text == "fake transcription"

    async def test_execute_with_language(self, tmp_path):
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"\x00")

        model = _make_stt_model()
        repo = FakeModelRepo([model])
        registry = STTProviderRegistry()
        registry.register(FakeSTTProvider())

        uc = TranscribeAudio(
            profile_resolver=STTProfileResolver(ModelResolver(repo)),
            provider_registry=registry,
        )
        result = await uc.execute(model_id="stt-default", audio_path=str(wav), language="en")
        assert result.language == "en"
