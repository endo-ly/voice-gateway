"""Registry for STT providers."""

from app.domain.errors import ProviderNotFoundError
from app.domain.interfaces.stt_provider import STTProvider


class STTProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, STTProvider] = {}

    def register(self, provider: STTProvider) -> None:
        self._providers[provider.provider_name] = provider

    def get(self, name: str) -> STTProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderNotFoundError(name)
        return provider
