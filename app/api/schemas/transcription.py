"""API schemas for STT transcription endpoints."""

from typing import Any

from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    text: str


class NativeTranscriptionData(BaseModel):
    text: str
    language: str
    duration_sec: float
    processing_ms: int
    provider: str
    model: str
    source: str = "unknown"
    audio: dict[str, Any] | None = None


class NativeTranscriptionResponse(BaseModel):
    ok: bool = True
    data: NativeTranscriptionData


class LatestTranscriptionData(BaseModel):
    text: str
    language: str
    duration_sec: float
    processing_ms: int
    provider: str
    model: str
    source: str = "unknown"
    audio: dict[str, Any] | None = None
    timestamp: str


class LatestTranscriptionResponse(BaseModel):
    ok: bool = True
    data: LatestTranscriptionData | None = None
