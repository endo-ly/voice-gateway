"""Tests for STTProviderRegistry."""

import pytest

from app.domain.errors import ProviderNotFoundError
from app.application.services.stt_provider_registry import STTProviderRegistry


class FakeSTTProvider:
    def __init__(self, name="fake_stt"):
        self.provider_name = name

    async def transcribe(self, request):
        pass

    def is_loaded(self):
        return True

    def capabilities(self):
        return {}


class TestSTTProviderRegistry:
    def test_register_and_resolve(self):
        registry = STTProviderRegistry()
        provider = FakeSTTProvider()
        registry.register(provider)
        assert registry.get("fake_stt") is provider

    def test_unknown_provider_raises(self):
        registry = STTProviderRegistry()
        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.get("nonexistent")
        assert exc_info.value.provider == "nonexistent"

    def test_register_multiple(self):
        registry = STTProviderRegistry()
        p1 = FakeSTTProvider("alpha")
        p2 = FakeSTTProvider("beta")
        registry.register(p1)
        registry.register(p2)
        assert registry.get("alpha") is p1
        assert registry.get("beta") is p2
