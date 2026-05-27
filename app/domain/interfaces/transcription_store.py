"""TranscriptionStore interface."""

from typing import Protocol

from app.domain.value_objects.transcription_result import TranscriptionResult


class TranscriptionStore(Protocol):
    def set_latest(self, result: TranscriptionResult, source: str) -> None: ...
    def get_latest(self) -> tuple[TranscriptionResult, str] | None: ...
