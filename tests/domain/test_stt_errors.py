"""Tests for STT domain errors."""

from app.domain.errors import (
    AudioValidationError,
    AudioTooLargeError,
    AudioTooLongError,
    TranscriptionFailedError,
    ModelNotLoadedError,
    VoiceGatewayError,
)


class TestSTTErrors:
    def test_audio_validation_error(self):
        e = AudioValidationError(code="INVALID_FORMAT", message="bad wav")
        assert e.code == "INVALID_FORMAT"
        assert str(e) == "bad wav"
        assert isinstance(e, VoiceGatewayError)

    def test_audio_too_large_error(self):
        e = AudioTooLargeError(max_size_mb=25)
        assert e.max_size_mb == 25
        assert "25" in str(e)
        assert isinstance(e, VoiceGatewayError)

    def test_audio_too_long_error(self):
        e = AudioTooLongError(max_seconds=30, actual_seconds=45)
        assert e.max_seconds == 30
        assert e.actual_seconds == 45
        assert isinstance(e, VoiceGatewayError)

    def test_transcription_failed_error(self):
        e = TranscriptionFailedError(provider_name="reazonspeech_k2", detail="OOM")
        assert e.provider_name == "reazonspeech_k2"
        assert isinstance(e, VoiceGatewayError)

    def test_model_not_loaded_error(self):
        e = ModelNotLoadedError(model_id="stt-default")
        assert e.model_id == "stt-default"
        assert isinstance(e, VoiceGatewayError)
