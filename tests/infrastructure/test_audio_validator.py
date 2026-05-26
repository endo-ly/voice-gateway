"""Tests for audio_validator."""

import wave
from pathlib import Path

import pytest

from app.domain.errors import AudioValidationError, AudioTooLongError
from app.infrastructure.providers.reazonspeech_k2.audio_validator import inspect_wav


def _write_wav(path: Path, sample_rate: int = 16000, channels: int = 1, duration_sec: float = 1.0):
    n_frames = int(sample_rate * duration_sec)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)


class TestInspectWav:
    def test_valid_wav(self, tmp_path):
        wav = tmp_path / "test.wav"
        _write_wav(wav, sample_rate=16000, channels=1, duration_sec=1.0)
        info = inspect_wav(wav)
        assert info.format == "wav"
        assert info.sample_rate == 16000
        assert info.channels == 1
        assert info.duration_sec == 1.0

    def test_rejects_non_wav(self, tmp_path):
        f = tmp_path / "test.mp3"
        f.write_bytes(b"fake")
        with pytest.raises(AudioValidationError) as exc_info:
            inspect_wav(f)
        assert exc_info.value.code == "INVALID_AUDIO_FORMAT"

    def test_rejects_too_long(self, tmp_path):
        wav = tmp_path / "long.wav"
        _write_wav(wav, sample_rate=16000, channels=1, duration_sec=35.0)
        with pytest.raises(AudioTooLongError):
            inspect_wav(wav, max_audio_seconds=30.0)

    def test_rejects_wrong_sample_rate_when_not_auto(self, tmp_path):
        wav = tmp_path / "test.wav"
        _write_wav(wav, sample_rate=8000, channels=1, duration_sec=1.0)
        with pytest.raises(AudioValidationError):
            inspect_wav(wav, auto_convert=False, preferred_sample_rate=16000)

    def test_auto_convert_accepts_any_rate(self, tmp_path):
        wav = tmp_path / "test.wav"
        _write_wav(wav, sample_rate=8000, channels=1, duration_sec=1.0)
        info = inspect_wav(wav, auto_convert=True)
        assert info.sample_rate == 8000
