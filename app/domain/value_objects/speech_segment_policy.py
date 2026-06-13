"""SpeechSegmentPolicy value object."""

from typing import Literal

from pydantic import BaseModel, model_validator

_MODE_CHAR_DEFAULTS: dict[str, dict[str, int]] = {
    "conversation": {
        "first_chunk_max_chars": 20,
        "min_chunk_chars": 8,
        "normal_max_chars": 80,
        "hard_max_chars": 120,
    },
    "narration": {
        "first_chunk_max_chars": 60,
        "min_chunk_chars": 20,
        "normal_max_chars": 160,
        "hard_max_chars": 240,
    },
}


class SpeechSegmentPolicy(BaseModel):
    enabled: bool = True
    mode: Literal["conversation", "narration"] = "conversation"

    first_chunk_max_chars: int | None = None
    min_chunk_chars: int | None = None
    normal_max_chars: int | None = None
    hard_max_chars: int | None = None

    split_punctuations: list[str] = ["。", "！", "？", ".", "!", "?", "\n"]
    soft_split_punctuations: list[str] = ["、", "，", "；", "：", ",", ";", ":"]

    merge_too_short_chunks: bool = True

    @model_validator(mode="after")
    def apply_mode_defaults(self) -> "SpeechSegmentPolicy":
        defaults = _MODE_CHAR_DEFAULTS[self.mode]
        for field_name, default_val in defaults.items():
            if getattr(self, field_name) is None:
                setattr(self, field_name, default_val)
        return self

    @classmethod
    def conversation(cls) -> "SpeechSegmentPolicy":
        return cls(mode="conversation")

    @classmethod
    def narration(cls) -> "SpeechSegmentPolicy":
        return cls(mode="narration")
