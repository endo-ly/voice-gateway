"""TranscriptionResult value object."""

from typing import Any

from pydantic import BaseModel


class TranscriptionResult(BaseModel):
    text: str
    language: str
    duration_sec: float
    processing_ms: int
    provider: str
    model: str
    source: str = "unknown"
    audio_info: dict[str, Any] | None = None
