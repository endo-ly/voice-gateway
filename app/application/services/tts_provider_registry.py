"""Registry for TTS providers."""

from app.domain.errors import ProviderNotFoundError
from app.domain.interfaces.tts_provider import TTSProvider


class TTSProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, TTSProvider] = {}

    def register(self, provider: TTSProvider) -> None:
        self._providers[provider.provider_name] = provider

    def get(self, name: str) -> TTSProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderNotFoundError(name)
        return provider
