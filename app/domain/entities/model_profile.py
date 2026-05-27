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

    @model_validator(mode="before")
    @classmethod
    def normalize_defaults_before(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data

        direction = data.get("direction", "tts")
        defaults = data.get("defaults") or {}

        if isinstance(defaults, (TTSModelDefaults, STTModelDefaults)):
            return data

        if direction == "stt":
            data["defaults"] = STTModelDefaults(**defaults)
        else:
            data["defaults"] = TTSModelDefaults(**defaults)

        return data
