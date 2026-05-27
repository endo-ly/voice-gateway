"""Tests for STTProfileResolver."""

import pytest

from app.application.services.model_resolver import ModelResolver
from app.application.services.stt_profile_resolver import STTProfileResolver
from app.domain.entities.model_profile import ModelProfile
from app.domain.errors import ModelNotFoundError


class FakeModelRepo:
    def __init__(self, models=None):
        self._models = {m.id: m for m in (models or [])}

    def get_by_id(self, model_id):
        if model_id not in self._models:
            raise ModelNotFoundError(model_id)
        return self._models[model_id]

    def list_all(self):
        return list(self._models.values())


def _make_stt_model(**overrides):
    defaults = {
        "id": "stt-default",
        "display_name": "STT Default",
        "direction": "stt",
        "provider": "reazonspeech_k2",
        "engine": "k2",
        "defaults": {"language": "ja", "max_audio_seconds": 30, "timeout_sec": 120},
        "provider_config": {"model_id": "test-model", "precision": "fp32"},
    }
    defaults.update(overrides)
    return ModelProfile.model_validate(defaults)


class TestSTTProfileResolver:
    def test_resolve_basic(self):
        model = _make_stt_model()
        repo = FakeModelRepo([model])
        resolver = STTProfileResolver(ModelResolver(repo))
        resolved_model, config = resolver.resolve("stt-default")
        assert resolved_model.id == "stt-default"
        assert "language" in config
        assert config["model_id"] == "test-model"

    def test_resolve_with_request_options(self):
        model = _make_stt_model()
        repo = FakeModelRepo([model])
        resolver = STTProfileResolver(ModelResolver(repo))
        _, config = resolver.resolve("stt-default", request_options={"language": "en"})
        assert config["language"] == "en"

    def test_resolve_rejects_tts_model(self):
        tts_model = ModelProfile(
            id="tts-default",
            display_name="TTS",
            provider="fake",
            engine="base",
        )
        repo = FakeModelRepo([tts_model])
        resolver = STTProfileResolver(ModelResolver(repo))
        with pytest.raises(ModelNotFoundError):
            resolver.resolve("tts-default")

    def test_priority_order(self):
        model = _make_stt_model(
            defaults={"language": "ja", "max_audio_seconds": 30, "timeout_sec": 120},
            provider_config={"language": "en", "model_id": "test"},
        )
        repo = FakeModelRepo([model])
        resolver = STTProfileResolver(ModelResolver(repo))
        _, config = resolver.resolve("stt-default", request_options={"language": "zh"})
        assert config["language"] == "zh"

    def test_missing_model_raises(self):
        repo = FakeModelRepo([])
        resolver = STTProfileResolver(ModelResolver(repo))
        with pytest.raises(ModelNotFoundError):
            resolver.resolve("nonexistent")
