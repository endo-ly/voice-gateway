"""Irodori TTS provider — switches between server and CLI backends."""

import asyncio
from typing import Literal

from pydantic import ValidationError

from app.domain.errors import InvalidProviderConfigError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.domain.value_objects.synthesis_result import SynthesisResult
from app.infrastructure.providers.irodori.cli_client import IrodoriCliClient
from app.infrastructure.providers.irodori.config_schemas import (
    IrodoriBaseConfig,
    IrodoriServerBaseConfig,
    IrodoriVoiceDesignConfig,
)
from app.infrastructure.providers.irodori.server_client import IrodoriServerClient


class IrodoriProvider:
    provider_name: str = "irodori"

    def __init__(
        self,
        irodori_repo_dir: str,
        tmp_dir: str,
        base_dir: str,
        timeout_sec: int = 120,
        max_concurrency: int = 1,
        backend: Literal["server", "cli"] = "server",
        server_base_url: str = "http://127.0.0.1:18790",
        server_api_key: str = "",
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._backend = backend

        if backend == "server":
            self._client: IrodoriServerClient | IrodoriCliClient = IrodoriServerClient(
                base_url=server_base_url,
                api_key=server_api_key,
                timeout_sec=timeout_sec,
            )
        else:
            self._client = IrodoriCliClient(
                irodori_repo_dir=irodori_repo_dir,
                tmp_dir=tmp_dir,
                base_dir=base_dir,
                timeout_sec=timeout_sec,
            )

    async def synthesize(self, request: ProviderSynthesisRequest) -> SynthesisResult:
        self._validate_config(request)
        async with self._semaphore:
            return await self._client.synthesize(request)

    def _validate_config(self, request: ProviderSynthesisRequest) -> None:
        if request.engine == "voicedesign":
            if self._backend == "server":
                raise InvalidProviderConfigError(
                    self.provider_name,
                    request.engine,
                    "voicedesign engine is not supported with server backend",
                )
            schema_cls = IrodoriVoiceDesignConfig
        elif self._backend == "server":
            schema_cls = IrodoriServerBaseConfig
        else:
            schema_cls = IrodoriBaseConfig
        try:
            schema_cls.model_validate(request.provider_config)
        except ValidationError as e:
            raise InvalidProviderConfigError(
                self.provider_name, request.engine, str(e)
            ) from e
