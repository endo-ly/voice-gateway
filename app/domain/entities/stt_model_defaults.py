"""STTModelDefaults for STT models."""

from pydantic import BaseModel


class STTModelDefaults(BaseModel):
    """STT用デフォルト値"""
    language: str = "ja"
    max_audio_seconds: float = 30
    timeout_sec: int = 120
