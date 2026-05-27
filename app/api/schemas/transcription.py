"""API schemas for STT transcription endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TranscriptionResponse(BaseModel):
    text: str


class NativeTranscriptionData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    language: str
    duration_sec: float = Field(serialization_alias="durationSec")
    processing_ms: int = Field(serialization_alias="processingMs")
    provider: str
    model: str
    source: str = "unknown"
    audio: dict[str, Any] | None = None


class NativeTranscriptionResponse(BaseModel):
    ok: bool = True
    data: NativeTranscriptionData


class LatestTranscriptionData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    language: str
    duration_sec: float = Field(serialization_alias="durationSec")
    processing_ms: int = Field(serialization_alias="processingMs")
    provider: str
    model: str
    source: str = "unknown"
    audio: dict[str, Any] | None = None
    timestamp: str


class LatestTranscriptionResponse(BaseModel):
    ok: bool = True
    data: LatestTranscriptionData | None = None
