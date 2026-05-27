"""Tests for STTModelDefaults."""

from app.domain.entities.stt_model_defaults import STTModelDefaults


class TestSTTModelDefaults:
    def test_default_values(self):
        d = STTModelDefaults()
        assert d.language == "ja"
        assert d.max_audio_seconds == 30
        assert d.timeout_sec == 120

    def test_custom_values(self):
        d = STTModelDefaults(language="en", max_audio_seconds=60, timeout_sec=90)
        assert d.language == "en"
        assert d.max_audio_seconds == 60
        assert d.timeout_sec == 90
