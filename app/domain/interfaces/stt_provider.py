"""STTProvider interface."""

from typing import Protocol, runtime_checkable

from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult


@runtime_checkable
class STTProvider(Protocol):
    provider_name: str

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult: ...

    def is_loaded(self) -> bool: ...

    def capabilities(self) -> dict: ...
