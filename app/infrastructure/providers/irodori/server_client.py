"""Irodori-TTS-Server HTTP client."""

from typing import Any

import httpx

from app.domain.errors import ProviderExecutionError, ProviderTimeoutError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.domain.value_objects.synthesis_result import SynthesisResult
from app.infrastructure.logging.logger import logger

_CLI_TO_SERVER_KEY_MAP: dict[str, str] = {
    "ref_wav_path": "ref_wav",
    "ref_latent_path": "ref_latent",
    "num_steps": "num_steps",
    "seed": "seed",
    "speaker_kv_scale": "speaker_kv_scale",
}

_SERVER_ONLY_KEYS: frozenset[str] = frozenset({
    "model_device",
    "codec_device",
    "model_precision",
    "codec_precision",
    "checkpoint",
    "max_text_len",
    "max_caption_len",
})


class IrodoriServerClient:
    """HTTP client for Irodori-TTS-Server."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:18790",
        model: str = "irodori",
        api_key: str = "",
        timeout_sec: int = 120,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_sec)

    async def synthesize(self, request: ProviderSynthesisRequest) -> SynthesisResult:
        payload = self._build_payload(request)
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            ) as client:
                logger.info(
                    "IrodoriServerClient synthesize model=%s voice=%s engine=%s text=%r",
                    request.model_id,
                    request.voice_id,
                    request.engine,
                    request.text,
                )
                response = await client.post(
                    "/v1/audio/speech",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                if not response.content:
                    raise ProviderExecutionError("irodori", "Irodori-TTS-Server returned empty audio")

                return SynthesisResult(audio_bytes=response.content)

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("irodori") from e
        except httpx.HTTPStatusError as e:
            detail = f"Irodori-TTS-Server HTTP {response.status_code}: {response.text[:500]}"
            raise ProviderExecutionError("irodori", detail) from e
        except httpx.HTTPError as e:
            raise ProviderExecutionError("irodori", str(e)) from e

    def _build_payload(self, request: ProviderSynthesisRequest) -> dict[str, Any]:
        cfg = request.provider_config
        irodori: dict[str, Any] = {
            "chunking_enabled": cfg.get("chunking_enabled", False),
        }

        for cli_key, server_key in _CLI_TO_SERVER_KEY_MAP.items():
            value = cfg.get(cli_key)
            if value is not None:
                irodori[server_key] = value

        for key, value in cfg.items():
            if key in _SERVER_ONLY_KEYS:
                continue
            if key in _CLI_TO_SERVER_KEY_MAP:
                continue
            if key in ("chunking_enabled",):
                continue
            irodori[key] = value

        return {
            "model": self._model,
            "input": request.text,
            "voice": cfg.get("voice"),
            "response_format": request.response_format,
            "irodori": irodori,
        }

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers
