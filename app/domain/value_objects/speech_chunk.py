"""SpeechChunk value object."""

from pydantic import BaseModel


class SpeechChunk(BaseModel):
    index: int
    text: str
    tts_text: str
