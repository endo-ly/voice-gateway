"""API schemas for OpenAI-compatible speech endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class SegmentOptions(BaseModel):
    enabled: bool = True
    mode: Literal["conversation", "narration"] = "conversation"


class BatchOptions(BaseModel):
    max_concurrency: int = Field(default=1, ge=1)
    ordered: bool = True
    stop_on_error: bool = True


class OpenAISpeechRequest(BaseModel):
    model: str
    voice: str
    input: str = Field(min_length=1)
    response_format: str = "wav"
    speed: float = 1.0
    stream_format: str | None = None
    segment: SegmentOptions = Field(default_factory=SegmentOptions)
    batch: BatchOptions = Field(default_factory=BatchOptions)
    extra_options: dict[str, Any] = Field(default_factory=dict)
