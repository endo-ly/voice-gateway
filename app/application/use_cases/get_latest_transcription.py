"""Get latest transcription use case."""

from app.domain.interfaces.transcription_store import TranscriptionStore
from app.domain.value_objects.transcription_result import TranscriptionResult


class GetLatestTranscription:
    def __init__(self, transcription_store: TranscriptionStore) -> None:
        self._store = transcription_store

    def execute(self) -> TranscriptionResult | None:
        return self._store.get_latest()
