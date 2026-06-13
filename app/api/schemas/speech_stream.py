"""API schemas for speech stream endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class SegmentOptions(BaseModel):
    enabled: bool = True
    mode: Literal["conversation", "narration"] = "conversation"


class BatchOptions(BaseModel):
    max_concurrency: int = 1
    ordered: bool = True
    stop_on_error: bool = True


class SpeechStreamRequest(BaseModel):
    model: str
    voice_id: str
    speech_text: str = Field(min_length=1)
    response_format: str = "wav"
    segment: SegmentOptions = Field(default_factory=SegmentOptions)
    batch: BatchOptions = Field(default_factory=BatchOptions)
    extra_options: dict[str, Any] = Field(default_factory=dict)
