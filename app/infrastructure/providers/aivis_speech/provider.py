"""AivisSpeech Engine TTS provider."""

import asyncio
from typing import Any

import httpx

from app.domain.errors import InvalidProviderConfigError, ProviderExecutionError, ProviderTimeoutError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.domain.value_objects.synthesis_result import SynthesisResult
from app.infrastructure.logging.logger import logger
from app.infrastructure.providers.aivis_speech.constants import AIVIS_HEALTH_PATH


class AivisSpeechProvider:
    provider_name: str = "aivis_speech"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:10101",
        timeout_sec: int = 120,
        max_concurrency: int = 1,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_sec)
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def synthesize(self, request: ProviderSynthesisRequest) -> SynthesisResult:
        speaker = self._speaker_id(request.provider_config)
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                    logger.info(
                        "AivisSpeech synthesize model=%s voice=%s speaker=%s text=%r",
                        request.model_id,
                        request.voice_id,
                        speaker,
                        request.text,
                    )
                    query = await self._audio_query(client, text=request.text, speaker=speaker)
                    self._apply_audio_query_options(query, request.provider_config)
                    audio_bytes = await self._synthesis(client, query=query, speaker=speaker)
                    return SynthesisResult(audio_bytes=audio_bytes)
            except httpx.TimeoutException as e:
                raise ProviderTimeoutError(self.provider_name) from e
            except httpx.HTTPError as e:
                raise ProviderExecutionError(self.provider_name, str(e)) from e

    async def list_speakers(self) -> list[dict[str, Any]]:
        """Fetch the raw speaker list from AivisSpeech Engine's /speakers.

        Returns AivisSpeech's native payload (list of speakers with styles).
        Caller is responsible for converting to VoiceProfiles.
        Raises ProviderExecutionError / ProviderTimeoutError on failure.
        """
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                    response = await client.get("/speakers")
                    self._raise_for_status(response, "speakers")
                    return response.json()
            except httpx.TimeoutException as e:
                raise ProviderTimeoutError(self.provider_name) from e
            except httpx.HTTPError as e:
                raise ProviderExecutionError(self.provider_name, str(e)) from e

    def _speaker_id(self, config: dict[str, Any]) -> int:
        speaker = config.get("speaker")
        if speaker is None:
            speaker = config.get("speaker_id")
        if not isinstance(speaker, int):
            raise InvalidProviderConfigError(
                self.provider_name,
                "voicevox-compatible",
                "provider_config.speaker must be an integer",
            )
        return speaker

    async def _audio_query(self, client: httpx.AsyncClient, text: str, speaker: int) -> dict[str, Any]:
        response = await client.post(
            "/audio_query",
            params={"text": text, "speaker": speaker},
        )
        self._raise_for_status(response, "audio_query")
        return response.json()

    def _apply_audio_query_options(self, query: dict[str, Any], config: dict[str, Any]) -> None:
        output_sampling_rate = config.get("output_sampling_rate")
        if output_sampling_rate is not None:
            if not isinstance(output_sampling_rate, int):
                raise InvalidProviderConfigError(
                    self.provider_name,
                    "voicevox-compatible",
                    "provider_config.output_sampling_rate must be an integer",
                )
            query["outputSamplingRate"] = output_sampling_rate

        output_stereo = config.get("output_stereo")
        if output_stereo is not None:
            if not isinstance(output_stereo, bool):
                raise InvalidProviderConfigError(
                    self.provider_name,
                    "voicevox-compatible",
                    "provider_config.output_stereo must be a boolean",
                )
            query["outputStereo"] = output_stereo

    async def _synthesis(self, client: httpx.AsyncClient, query: dict[str, Any], speaker: int) -> bytes:
        response = await client.post(
            "/synthesis",
            params={"speaker": speaker},
            json=query,
        )
        self._raise_for_status(response, "synthesis")
        if not response.content:
            raise ProviderExecutionError(self.provider_name, "synthesis returned empty audio")
        return response.content

    async def health(self) -> dict[str, bool | str]:
        """Check engine reachability for health endpoints."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._base_url}{AIVIS_HEALTH_PATH}")
            return {"engineReachable": response.status_code == 200, "baseUrl": self._base_url}
        except httpx.HTTPError:
            return {"engineReachable": False, "baseUrl": self._base_url}

    def _raise_for_status(self, response: httpx.Response, operation: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = f"{operation} failed with HTTP {response.status_code}: {response.text[:500]}"
            raise ProviderExecutionError(self.provider_name, detail) from e
