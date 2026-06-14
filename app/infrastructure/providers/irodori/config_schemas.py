"""Pydantic schemas for Irodori provider_config validation.

These validate the MERGED config (5-layer merge result) before
the provider executes, catching missing required keys early.
"""

from pydantic import BaseModel, Field, model_validator


class IrodoriBaseConfig(BaseModel):
    """Merged config for Irodori base engine (zero-shot voice cloning) — CLI backend."""

    checkpoint: str
    ref_latent_path: str | None = None
    ref_wav_path: str | None = None
    model_device: str = "cpu"
    codec_device: str = "cpu"
    model_precision: str = "fp32"
    codec_precision: str = "fp32"
    num_steps: int = 28
    seed: int = 0
    speaker_kv_scale: float = 1.0
    max_text_len: int | None = None
    max_caption_len: int | None = None

    @model_validator(mode="after")
    def validate_ref_source(self) -> "IrodoriBaseConfig":
        if not self.ref_latent_path and not self.ref_wav_path:
            raise ValueError(
                "ref_latent_path or ref_wav_path is required for base engine"
            )
        return self


class IrodoriServerBaseConfig(BaseModel):
    """Merged config for Irodori base engine — server backend.

    The server manages checkpoint, devices, and precision internally,
    so those are not required here.
    """

    ref_latent_path: str | None = None
    ref_wav_path: str | None = None
    num_steps: int = 28
    seed: int = 0
    speaker_kv_scale: float = 1.0

    @model_validator(mode="after")
    def validate_ref_source(self) -> "IrodoriServerBaseConfig":
        if not self.ref_latent_path and not self.ref_wav_path:
            raise ValueError(
                "ref_latent_path or ref_wav_path is required for base engine"
            )
        return self


class IrodoriVoiceDesignConfig(BaseModel):
    """Merged config for Irodori VoiceDesign engine (caption-conditioned)."""

    checkpoint: str
    caption: str
    model_device: str = "cpu"
    codec_device: str = "cpu"
    model_precision: str = "fp32"
    codec_precision: str = "fp32"
    num_steps: int = 28
    seed: int = 0
    max_text_len: int | None = None
    max_caption_len: int | None = None
