"""Tests for SpeechBatchSynthesizer."""

import pytest

from app.application.services.option_merger import OptionMerger
from app.application.services.speech_batch_synthesizer import SpeechBatchSynthesizer
from app.application.services.tts_profile_resolver import TTSProfileResolver
from app.application.services.tts_provider_registry import TTSProviderRegistry
from app.domain.entities.model_profile import ModelProfile, TTSModelDefaults
from app.domain.entities.voice_profile import VoiceBinding, VoiceDefaults, VoiceProfile
from app.domain.value_objects.speech_batch_policy import SpeechBatchPolicy
from app.domain.value_objects.speech_chunk import SpeechChunk
from app.domain.value_objects.speech_chunk_result import SpeechChunkError, SpeechChunkResult


WAV_BYTES = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"


class FakeProvider:
    provider_name = "fake"

    def __init__(self, fail_on_index: int | None = None) -> None:
        self._fail_on_index = fail_on_index
        self.calls: list[str] = []

    async def synthesize(self, request) -> object:
        self.calls.append(request.text)
        if self._fail_on_index is not None:
            from app.domain.errors import ProviderExecutionError
            for chunk_text in [c.tts_text for c in _make_chunks()]:
                if request.text == chunk_text:
                    idx = _make_chunks().index(
                        next(c for c in _make_chunks() if c.tts_text == request.text)
                    )
                    if idx == self._fail_on_index:
                        raise ProviderExecutionError("fake", "simulated failure")
        from app.domain.value_objects.synthesis_result import SynthesisResult
        return SynthesisResult(audio_bytes=WAV_BYTES)


def _make_chunks() -> list[SpeechChunk]:
    return [
        SpeechChunk(index=0, text="一つ目。", tts_text="一つ目。"),
        SpeechChunk(index=1, text="二つ目。", tts_text="二つ目。"),
        SpeechChunk(index=2, text="三つ目。", tts_text="三つ目。"),
    ]


def _make_resolver_and_registry(provider: FakeProvider):
    registry = TTSProviderRegistry()
    registry.register(provider)

    from app.application.services.model_resolver import ModelResolver

    class StubModelRepo:
        def list_all(self):
            return [
                ModelProfile(
                    id="tts-default",
                    display_name="Default",
                    provider="fake",
                    engine="base",
                    provider_config={},
                    defaults=TTSModelDefaults(),
                )
            ]

        def get_by_id(self, model_id: str):
            return ModelProfile(
                id="tts-default",
                display_name="Default",
                provider="fake",
                engine="base",
                provider_config={},
                defaults=TTSModelDefaults(),
            )

    class StubVoiceRepo:
        def get_by_id(self, voice_id: str):
            return VoiceProfile(
                voice_id="test-voice",
                display_name="Test Voice",
                defaults=VoiceDefaults(),
                bindings={"tts-default": VoiceBinding(provider_config={})},
            )

    resolver = TTSProfileResolver(
        model_resolver=ModelResolver(StubModelRepo()),
        voice_repo=StubVoiceRepo(),
        option_merger=OptionMerger(),
    )
    return resolver, registry


@pytest.mark.asyncio
async def test_batch_synthesizer_returns_results_in_order():
    provider = FakeProvider()
    resolver, registry = _make_resolver_and_registry(provider)
    synth = SpeechBatchSynthesizer(resolver, registry)

    results = await synth.synthesize_batch(
        chunks=_make_chunks(),
        model_id="tts-default",
        voice_id="test-voice",
    )

    assert len(results) == 3
    for i, r in enumerate(results):
        assert isinstance(r, SpeechChunkResult)
        assert r.index == i
        assert r.audio_bytes == WAV_BYTES


@pytest.mark.asyncio
async def test_batch_synthesizer_sequential_with_max_concurrency_1():
    provider = FakeProvider()
    resolver, registry = _make_resolver_and_registry(provider)
    synth = SpeechBatchSynthesizer(resolver, registry)

    policy = SpeechBatchPolicy(max_concurrency=1)
    results = await synth.synthesize_batch(
        chunks=_make_chunks(),
        model_id="tts-default",
        voice_id="test-voice",
        batch_policy=policy,
    )

    assert len(results) == 3
    assert provider.calls == ["一つ目。", "二つ目。", "三つ目。"]


@pytest.mark.asyncio
async def test_batch_synthesizer_stop_on_error():
    provider = FakeProvider(fail_on_index=1)
    resolver, registry = _make_resolver_and_registry(provider)
    synth = SpeechBatchSynthesizer(resolver, registry)

    policy = SpeechBatchPolicy(max_concurrency=1, stop_on_error=True)
    results = await synth.synthesize_batch(
        chunks=_make_chunks(),
        model_id="tts-default",
        voice_id="test-voice",
        batch_policy=policy,
    )

    assert len(results) == 2
    assert isinstance(results[0], SpeechChunkResult)
    assert results[0].index == 0
    assert isinstance(results[1], SpeechChunkError)
    assert results[1].index == 1


@pytest.mark.asyncio
async def test_batch_synthesizer_stream_yields_events():
    provider = FakeProvider()
    resolver, registry = _make_resolver_and_registry(provider)
    synth = SpeechBatchSynthesizer(resolver, registry)

    events = []
    async for event in synth.synthesize_stream(
        chunks=_make_chunks(),
        model_id="tts-default",
        voice_id="test-voice",
    ):
        events.append(event)

    assert len(events) == 3
    for event in events:
        assert event.result is not None
        assert event.error is None


@pytest.mark.asyncio
async def test_batch_synthesizer_stream_stops_on_error():
    provider = FakeProvider(fail_on_index=0)
    resolver, registry = _make_resolver_and_registry(provider)
    synth = SpeechBatchSynthesizer(resolver, registry)

    policy = SpeechBatchPolicy(stop_on_error=True)
    events = []
    async for event in synth.synthesize_stream(
        chunks=_make_chunks(),
        model_id="tts-default",
        voice_id="test-voice",
        batch_policy=policy,
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0].is_error
    assert events[0].error.index == 0


@pytest.mark.asyncio
async def test_batch_synthesizer_continue_on_error_when_stop_on_error_false():
    provider = FakeProvider(fail_on_index=1)
    resolver, registry = _make_resolver_and_registry(provider)
    synth = SpeechBatchSynthesizer(resolver, registry)

    policy = SpeechBatchPolicy(max_concurrency=1, stop_on_error=False)
    results = await synth.synthesize_batch(
        chunks=_make_chunks(),
        model_id="tts-default",
        voice_id="test-voice",
        batch_policy=policy,
    )

    assert len(results) == 3
    assert isinstance(results[0], SpeechChunkResult)
    assert isinstance(results[1], SpeechChunkError)
    assert results[1].code == "provider_error"
    assert isinstance(results[2], SpeechChunkResult)


@pytest.mark.asyncio
async def test_batch_synthesizer_does_not_reference_provider_name():
    provider = FakeProvider()
    resolver, registry = _make_resolver_and_registry(provider)
    synth = SpeechBatchSynthesizer(resolver, registry)

    results = await synth.synthesize_batch(
        chunks=_make_chunks(),
        model_id="tts-default",
        voice_id="test-voice",
    )

    assert all(isinstance(r, SpeechChunkResult) for r in results)
