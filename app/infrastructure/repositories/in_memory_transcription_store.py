"""In-memory implementation of TranscriptionStore."""

from datetime import UTC, datetime

from app.domain.value_objects.transcription_result import TranscriptionResult


class InMemoryTranscriptionStore:
    def __init__(self) -> None:
        self._latest: TranscriptionResult | None = None
        self._timestamp: str | None = None

    def set_latest(self, result: TranscriptionResult, source: str = "unknown") -> None:
        updated = result.model_copy(update={"source": source})
        self._latest = updated
        self._timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def get_latest(self) -> tuple[TranscriptionResult, str] | None:
        if self._latest is None:
            return None
        return self._latest, self._timestamp or ""

    @property
    def timestamp(self) -> str | None:
        return self._timestamp
