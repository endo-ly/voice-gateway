"""Tests for TTSProviderRegistry."""

import pytest

from app.domain.errors import ProviderNotFoundError
from app.application.services.tts_provider_registry import TTSProviderRegistry
from app.infrastructure.providers.fake.provider import FakeProvider


class TestTTSProviderRegistry:
    def test_register_and_resolve(self):
        registry = TTSProviderRegistry()
        fake = FakeProvider()
        registry.register(fake)
        assert registry.get("fake") is fake

    def test_unknown_provider_raises(self):
        registry = TTSProviderRegistry()
        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.get("nonexistent")
        assert exc_info.value.provider == "nonexistent"

    def test_register_multiple(self):
        registry = TTSProviderRegistry()
        fake1 = FakeProvider()
        fake1.provider_name = "alpha"
        fake2 = FakeProvider()
        fake2.provider_name = "beta"
        registry.register(fake1)
        registry.register(fake2)
        assert registry.get("alpha") is fake1
        assert registry.get("beta") is fake2

    def test_overwrite_existing(self):
        registry = TTSProviderRegistry()
        fake1 = FakeProvider()
        fake2 = FakeProvider()
        registry.register(fake1)
        registry.register(fake2)
        assert registry.get("fake") is fake2
