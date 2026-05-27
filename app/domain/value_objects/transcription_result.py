"""TranscriptionResult value object."""

from typing import Any

from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    text: str
    language: str
    duration_sec: float = Field(ge=0)
    processing_ms: int = Field(ge=0)
    provider: str
    model: str
    source: str = "unknown"
    audio_info: dict[str, Any] | None = None
