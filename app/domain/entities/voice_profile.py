"""VoiceProfile entity."""

from typing import Any

from pydantic import BaseModel, Field


class VoiceDefaults(BaseModel):
    preferred_model: str = "tts-default"
    response_format: str = "wav"
    speed: float = 1.0


class VoiceBinding(BaseModel):
    provider_config: dict[str, Any] = Field(default_factory=dict)


class VoiceProfile(BaseModel):
    voice_id: str
    display_name: str
    description: str = ""
    generation_prompt: str = ""
    defaults: VoiceDefaults = Field(default_factory=VoiceDefaults)
    bindings: dict[str, VoiceBinding] = Field(default_factory=dict)
