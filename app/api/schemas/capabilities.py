"""API schemas for capabilities endpoint."""

from pydantic import BaseModel


class DirectionCapabilities(BaseModel):
    enabled: bool
    providers: list[str]


class CapabilitiesResponse(BaseModel):
    tts: DirectionCapabilities
    stt: DirectionCapabilities
