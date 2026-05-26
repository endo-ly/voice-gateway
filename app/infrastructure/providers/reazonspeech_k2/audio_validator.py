"""WAV audio validation for ReazonSpeech K2 provider."""

from pathlib import Path
import wave

from app.domain.errors import AudioValidationError, AudioTooLongError
from app.infrastructure.providers.reazonspeech_k2.types import AudioInfo


def inspect_wav(
    path: Path,
    max_audio_seconds: float = 30.0,
    accepted_formats: tuple[str, ...] = ("wav",),
    auto_convert: bool = True,
    preferred_sample_rate: int = 16000,
    preferred_channels: int = 1,
) -> AudioInfo:
    if path.suffix.lower().lstrip(".") not in accepted_formats:
        raise AudioValidationError(
            code="INVALID_AUDIO_FORMAT",
            message=f"Unsupported audio format. Accepted: {accepted_formats}",
        )

    try:
        with wave.open(str(path), "rb") as wav:
            sample_rate = wav.getframerate()
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            frames = wav.getnframes()
    except wave.Error as error:
        raise AudioValidationError(
            code="INVALID_AUDIO_FORMAT",
            message="Invalid WAV file",
        ) from error

    duration = frames / sample_rate if sample_rate > 0 else 0.0
    if duration > max_audio_seconds:
        raise AudioTooLongError(max_seconds=max_audio_seconds, actual_seconds=duration)

    if not auto_convert:
        if sample_rate != preferred_sample_rate:
            raise AudioValidationError(
                code="INVALID_AUDIO_FORMAT",
                message=f"WAV sample rate must be {preferred_sample_rate}Hz",
            )
        if channels != preferred_channels:
            raise AudioValidationError(
                code="INVALID_AUDIO_FORMAT",
                message=f"WAV must have {preferred_channels} channel(s)",
            )

    return AudioInfo(
        format="wav",
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        frames=frames,
        duration_sec=duration,
    )
