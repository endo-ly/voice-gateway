"""Provider-agnostic batch synthesizer for chunked TTS generation."""

import asyncio
from typing import Any

from app.application.services.tts_profile_resolver import TTSProfileResolver
from app.application.services.tts_provider_registry import TTSProviderRegistry
from app.domain.errors import VoiceGatewayError
from app.domain.value_objects.speech_batch_policy import SpeechBatchPolicy
from app.domain.value_objects.speech_chunk import SpeechChunk
from app.domain.value_objects.speech_chunk_result import SpeechChunkError, SpeechChunkResult
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest


class BatchSynthesisEvent:
    """Union type for batch synthesis stream events."""

    def __init__(
        self,
        result: SpeechChunkResult | None = None,
        error: SpeechChunkError | None = None,
    ) -> None:
        self.result = result
        self.error = error

    @property
    def is_error(self) -> bool:
        return self.error is not None


class SpeechBatchSynthesizer:
    """Synthesizes chunked speech via a TTS provider."""

    def __init__(
        self,
        profile_resolver: TTSProfileResolver,
        provider_registry: TTSProviderRegistry,
    ) -> None:
        self._resolver = profile_resolver
        self._registry = provider_registry

    async def synthesize_batch(
        self,
        chunks: list[SpeechChunk],
        model_id: str,
        voice_id: str,
        response_format: str = "wav",
        extra_options: dict | None = None,
        batch_policy: SpeechBatchPolicy | None = None,
    ) -> list[SpeechChunkResult | SpeechChunkError]:
        """Synthesize all chunks and return results in index order."""
        batch_policy = batch_policy or SpeechBatchPolicy()
        results: dict[int, SpeechChunkResult | SpeechChunkError] = {}

        model, voice, merged_config = self._resolver.resolve(
            model_id, voice_id, request_options=extra_options
        )
        provider = self._registry.get(model.provider)

        if batch_policy.max_concurrency <= 1:
            for chunk in chunks:
                event = await self._synthesize_chunk(
                    chunk,
                    model_id=model.id,
                    voice_id=voice.voice_id,
                    provider_name=model.provider,
                    engine=model.engine,
                    merged_config=merged_config,
                    response_format=response_format,
                )
                results[chunk.index] = event.error or event.result  # type: ignore[assignment]
                if event.is_error and batch_policy.stop_on_error:
                    break
        else:
            sem = asyncio.Semaphore(batch_policy.max_concurrency)
            results = await self._synthesize_concurrent(
                chunks,
                sem=sem,
                model_id=model.id,
                voice_id=voice.voice_id,
                provider_name=model.provider,
                engine=model.engine,
                merged_config=merged_config,
                response_format=response_format,
                stop_on_error=batch_policy.stop_on_error,
            )

        ordered: list[SpeechChunkResult | SpeechChunkError] = []
        for chunk in chunks:
            item = results.get(chunk.index)
            if item is not None:
                ordered.append(item)
            if isinstance(item, SpeechChunkError) and batch_policy.stop_on_error:
                break

        return ordered

    async def synthesize_stream(
        self,
        chunks: list[SpeechChunk],
        model_id: str,
        voice_id: str,
        response_format: str = "wav",
        extra_options: dict | None = None,
        batch_policy: SpeechBatchPolicy | None = None,
    ):
        """Async generator yielding events as each chunk completes."""
        batch_policy = batch_policy or SpeechBatchPolicy()

        model, voice, merged_config = self._resolver.resolve(
            model_id, voice_id, request_options=extra_options
        )
        provider = self._registry.get(model.provider)

        for chunk in chunks:
            event = await self._synthesize_chunk(
                chunk,
                model_id=model.id,
                voice_id=voice.voice_id,
                provider_name=model.provider,
                engine=model.engine,
                merged_config=merged_config,
                response_format=response_format,
            )
            yield event
            if event.is_error and batch_policy.stop_on_error:
                return

    async def _synthesize_chunk(
        self,
        chunk: SpeechChunk,
        model_id: str,
        voice_id: str,
        provider_name: str,
        engine: str,
        merged_config: dict[str, Any],
        response_format: str,
    ) -> BatchSynthesisEvent:
        try:
            provider = self._registry.get(provider_name)
            request = ProviderSynthesisRequest(
                model_id=model_id,
                voice_id=voice_id,
                text=chunk.tts_text,
                response_format=response_format,
                provider=provider_name,
                engine=engine,
                provider_config=merged_config,
            )
            result = await provider.synthesize(request)
            return BatchSynthesisEvent(
                result=SpeechChunkResult(
                    index=chunk.index,
                    text=chunk.text,
                    tts_text=chunk.tts_text,
                    audio_bytes=result.audio_bytes,
                    media_type=result.media_type,
                    format=result.format,
                )
            )
        except VoiceGatewayError as e:
            return BatchSynthesisEvent(
                error=SpeechChunkError(
                    index=chunk.index,
                    text=chunk.text,
                    tts_text=chunk.tts_text,
                    message=str(e),
                )
            )

    async def _synthesize_concurrent(
        self,
        chunks: list[SpeechChunk],
        sem: asyncio.Semaphore,
        model_id: str,
        voice_id: str,
        provider_name: str,
        engine: str,
        merged_config: dict[str, Any],
        response_format: str,
        stop_on_error: bool,
    ) -> dict[int, SpeechChunkResult | SpeechChunkError]:
        results: dict[int, SpeechChunkResult | SpeechChunkError] = {}
        stop_flag = asyncio.Event()

        async def worker(chunk: SpeechChunk) -> None:
            if stop_flag.is_set():
                return
            async with sem:
                if stop_flag.is_set():
                    return
                event = await self._synthesize_chunk(
                    chunk,
                    model_id=model_id,
                    voice_id=voice_id,
                    provider_name=provider_name,
                    engine=engine,
                    merged_config=merged_config,
                    response_format=response_format,
                )
                results[chunk.index] = event.error or event.result  # type: ignore[assignment]
                if event.is_error and stop_on_error:
                    stop_flag.set()

        await asyncio.gather(*(worker(c) for c in chunks))
        return results
