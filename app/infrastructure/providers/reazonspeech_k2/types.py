"""Audio metadata types for ReazonSpeech K2 provider."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioInfo:
    format: str
    sample_rate: int
    channels: int
    sample_width: int
    frames: int
    duration_sec: float
