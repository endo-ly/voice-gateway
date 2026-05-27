"""Tests for ModelProfile entity."""

import pytest
from pydantic import ValidationError

from app.domain.entities.model_profile import TTSModelDefaults, ModelProfile
from app.domain.entities.stt_model_defaults import STTModelDefaults


class TestTTSModelDefaults:
    def test_default_values(self):
        d = TTSModelDefaults()
        assert d.response_format == "wav"
        assert d.speed == 1.0
        assert d.timeout_sec == 120

    def test_custom_values(self):
        d = TTSModelDefaults(response_format="wav", speed=1.0, timeout_sec=60)
        assert d.timeout_sec == 60


class TestModelProfile:
    def test_valid_minimal(self):
        mp = ModelProfile(
            id="test-model",
            display_name="Test Model",
            provider="fake",
            engine="base",
        )
        assert mp.id == "test-model"
        assert mp.object == "model"
        assert mp.display_name == "Test Model"
        assert mp.provider == "fake"
        assert mp.engine == "base"

    def test_with_all_fields(self):
        mp = ModelProfile(
            id="tts-default",
            display_name="Default TTS",
            provider="irodori",
            engine="base",
            defaults=TTSModelDefaults(response_format="wav", speed=1.0, timeout_sec=120),
            provider_config={
                "checkpoint": "Aratako/Irodori-TTS-500M-v2",
                "model_device": "cuda",
            },
        )
        assert mp.provider_config["checkpoint"] == "Aratako/Irodori-TTS-500M-v2"
        assert mp.defaults.timeout_sec == 120

    def test_missing_id_raises(self):
        with pytest.raises(ValidationError):
            ModelProfile(
                display_name="Test",
                provider="fake",
                engine="base",
            )

    def test_missing_provider_raises(self):
        with pytest.raises(ValidationError):
            ModelProfile(
                id="test",
                display_name="Test",
                engine="base",
            )

    def test_missing_engine_raises(self):
        with pytest.raises(ValidationError):
            ModelProfile(
                id="test",
                display_name="Test",
                provider="fake",
            )

    def test_defaults_is_optional_with_defaults(self):
        mp = ModelProfile(
            id="test",
            display_name="Test",
            provider="fake",
            engine="base",
        )
        assert mp.defaults.response_format == "wav"
        assert mp.defaults.speed == 1.0

    def test_provider_config_defaults_to_empty_dict(self):
        mp = ModelProfile(
            id="test",
            display_name="Test",
            provider="fake",
            engine="base",
        )
        assert mp.provider_config == {}

    def test_from_yaml_like_dict(self):
        data = {
            "id": "tts-default",
            "object": "model",
            "display_name": "Default TTS",
            "provider": "irodori",
            "engine": "base",
            "defaults": {"response_format": "wav", "speed": 1.0, "timeout_sec": 120},
            "provider_config": {
                "checkpoint": "Aratako/Irodori-TTS-500M-v2",
                "model_device": "cuda",
            },
        }
        mp = ModelProfile.model_validate(data)
        assert mp.id == "tts-default"
        assert mp.provider == "irodori"
        assert mp.defaults.timeout_sec == 120
        assert mp.provider_config["model_device"] == "cuda"

    def test_tts_dict_defaults_produces_tts_model_defaults(self):
        mp = ModelProfile(
            id="test",
            display_name="Test",
            provider="fake",
            engine="base",
            defaults={"response_format": "mp3", "speed": 1.5, "timeout_sec": 60},
        )
        assert isinstance(mp.defaults, TTSModelDefaults)
        assert mp.defaults.response_format == "mp3"
        assert mp.defaults.speed == 1.5

    def test_no_defaults_key_produces_tts_model_defaults(self):
        mp = ModelProfile(
            id="test",
            display_name="Test",
            provider="fake",
            engine="base",
        )
        assert isinstance(mp.defaults, TTSModelDefaults)
        assert mp.defaults.response_format == "wav"
