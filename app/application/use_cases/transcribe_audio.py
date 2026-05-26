"""Transcribe audio use case."""

from time import perf_counter

from app.application.services.stt_profile_resolver import STTProfileResolver
from app.application.services.stt_provider_registry import STTProviderRegistry
from app.domain.interfaces.transcription_store import TranscriptionStore
from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult


class TranscribeAudio:
    def __init__(
        self,
        profile_resolver: STTProfileResolver,
        provider_registry: STTProviderRegistry,
        transcription_store: TranscriptionStore | None = None,
    ) -> None:
        self._resolver = profile_resolver
        self._registry = provider_registry
        self._store = transcription_store

    async def execute(
        self,
        model_id: str,
        audio_path: str,
        source: str = "unknown",
        language: str | None = None,
    ) -> TranscriptionResult:
        request_options: dict = {}
        if language is not None:
            request_options["language"] = language

        model, config = self._resolver.resolve(
            model_id, request_options=request_options if request_options else None
        )

        provider = self._registry.get(model.provider)

        request = TranscriptionRequest(
            model_id=model.id,
            audio_path=audio_path,
            language=config.get("language", "ja"),
            provider=model.provider,
            engine=model.engine,
            provider_config=config,
        )

        started_at = perf_counter()
        result = await provider.transcribe(request)
        elapsed_ms = round((perf_counter() - started_at) * 1000)

        result = result.model_copy(update={
            "source": source,
            "processing_ms": elapsed_ms,
        })

        if self._store is not None:
            self._store.set_latest(result, source=source)

        return result
