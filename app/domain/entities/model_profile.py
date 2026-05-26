"""ModelProfile entity."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.domain.entities.stt_model_defaults import STTModelDefaults


class TTSModelDefaults(BaseModel):
    response_format: str = "wav"
    speed: float = 1.0
    timeout_sec: int = 120


class ModelProfile(BaseModel):
    id: str
    object: str = "model"
    display_name: str
    direction: Literal["tts", "stt"] = "tts"
    provider: str
    engine: str
    defaults: TTSModelDefaults | STTModelDefaults = Field(default_factory=TTSModelDefaults)
    provider_config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_defaults(self) -> "ModelProfile":
        if isinstance(self.defaults, dict):
            self.defaults = (
                STTModelDefaults(**self.defaults)
                if self.direction == "stt"
                else TTSModelDefaults(**self.defaults)
            )
        return self
