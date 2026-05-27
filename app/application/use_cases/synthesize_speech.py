"""Synthesize speech use case."""

from app.application.services.tts_profile_resolver import TTSProfileResolver
from app.application.services.tts_provider_registry import TTSProviderRegistry
from app.domain.errors import UnsupportedResponseFormatError, UnsupportedSpeedError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.domain.value_objects.synthesis_result import SynthesisResult


class SynthesizeSpeech:
    def __init__(
        self,
        profile_resolver: TTSProfileResolver,
        provider_registry: TTSProviderRegistry,
    ) -> None:
        self._resolver = profile_resolver
        self._registry = provider_registry

    async def execute(
        self,
        model_id: str,
        voice_id: str,
        text: str,
        response_format: str = "wav",
        speed: float = 1.0,
        extra_options: dict | None = None,
    ) -> SynthesisResult:
        if response_format != "wav":
            raise UnsupportedResponseFormatError(response_format)
        if speed != 1.0:
            raise UnsupportedSpeedError(speed)

        request_options: dict = {"response_format": response_format, "speed": speed}
        if extra_options:
            request_options.update(extra_options)

        model, voice, merged_config = self._resolver.resolve(
            model_id, voice_id, request_options=request_options
        )

        provider = self._registry.get(model.provider)

        request = ProviderSynthesisRequest(
            model_id=model.id,
            voice_id=voice.voice_id,
            text=text,
            response_format=response_format,
            speed=speed,
            provider=model.provider,
            engine=model.engine,
            provider_config=merged_config,
        )

        return await provider.synthesize(request)
