"""SpeechChunkResult value object."""

from pydantic import BaseModel


class SpeechChunkResult(BaseModel):
    index: int
    text: str
    tts_text: str
    audio_bytes: bytes
    media_type: str = "audio/wav"
    format: str = "wav"


class SpeechChunkError(BaseModel):
    index: int
    text: str
    tts_text: str
    message: str
    code: str = "provider_error"
