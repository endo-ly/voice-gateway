"""TranscriptionRequest value object."""

from typing import Any

from pydantic import BaseModel, Field


class TranscriptionRequest(BaseModel):
    model_id: str
    audio_path: str
    language: str = "ja"
    provider: str
    engine: str
    provider_config: dict[str, Any] = Field(default_factory=dict)
