"""Tests for STT value objects."""

from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult


class TestTranscriptionRequest:
    def test_valid_request(self):
        req = TranscriptionRequest(
            model_id="stt-default",
            audio_path="/tmp/test.wav",
            language="ja",
            provider="reazonspeech_k2",
            engine="k2",
        )
        assert req.model_id == "stt-default"
        assert req.language == "ja"

    def test_default_language(self):
        req = TranscriptionRequest(
            model_id="stt-default",
            audio_path="/tmp/test.wav",
            provider="reazonspeech_k2",
            engine="k2",
        )
        assert req.language == "ja"

    def test_with_provider_config(self):
        req = TranscriptionRequest(
            model_id="stt-default",
            audio_path="/tmp/test.wav",
            provider="reazonspeech_k2",
            engine="k2",
            provider_config={"model_id": "reazon-research/reazonspeech-k2-v2"},
        )
        assert req.provider_config["model_id"] == "reazon-research/reazonspeech-k2-v2"


class TestTranscriptionResult:
    def test_valid_result(self):
        result = TranscriptionResult(
            text="hello world",
            language="ja",
            duration_sec=5.0,
            processing_ms=1200,
            provider="reazonspeech_k2",
            model="reazon-research/reazonspeech-k2-v2",
        )
        assert result.text == "hello world"
        assert result.source == "unknown"
        assert result.audio_info is None

    def test_with_all_fields(self):
        result = TranscriptionResult(
            text="test",
            language="ja",
            duration_sec=3.0,
            processing_ms=500,
            provider="reazonspeech_k2",
            model="test-model",
            source="stackchan",
            audio_info={"sampleRate": 16000, "channels": 1},
        )
        assert result.source == "stackchan"
        assert result.audio_info["sampleRate"] == 16000
