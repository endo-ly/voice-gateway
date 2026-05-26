"""Tests for ModelProfile with STT direction."""

import pytest
from pydantic import ValidationError

from app.domain.entities.model_profile import ModelProfile, TTSModelDefaults
from app.domain.entities.stt_model_defaults import STTModelDefaults


class TestModelProfileSTTDirection:
    def test_stt_direction_with_stt_defaults(self):
        mp = ModelProfile(
            id="stt-default",
            display_name="STT Default",
            direction="stt",
            provider="reazonspeech_k2",
            engine="k2",
            defaults=STTModelDefaults(language="ja", max_audio_seconds=30),
        )
        assert mp.direction == "stt"
        assert isinstance(mp.defaults, STTModelDefaults)
        assert mp.defaults.language == "ja"

    def test_stt_direction_from_dict_auto_normalized(self):
        data = {
            "id": "stt-default",
            "display_name": "STT Default",
            "direction": "stt",
            "provider": "reazonspeech_k2",
            "engine": "k2",
            "defaults": {"language": "en", "max_audio_seconds": 60, "timeout_sec": 90},
        }
        mp = ModelProfile.model_validate(data)
        assert mp.direction == "stt"
        assert isinstance(mp.defaults, STTModelDefaults)
        assert mp.defaults.language == "en"

    def test_tts_direction_from_dict_stays_tts_defaults(self):
        data = {
            "id": "tts-default",
            "display_name": "TTS Default",
            "direction": "tts",
            "provider": "fake",
            "engine": "base",
            "defaults": {"response_format": "wav", "speed": 1.0, "timeout_sec": 120},
        }
        mp = ModelProfile.model_validate(data)
        assert mp.direction == "tts"
        assert isinstance(mp.defaults, TTSModelDefaults)

    def test_default_direction_is_tts(self):
        mp = ModelProfile(
            id="test",
            display_name="Test",
            provider="fake",
            engine="base",
        )
        assert mp.direction == "tts"
