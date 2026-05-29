"""Tests for health route."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealth:
    async def test_health_returns_200_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "mode" in body
        assert "providers" in body

    async def test_health_providers_have_registered_and_loaded(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        providers = body["providers"]
        for direction in ("tts", "stt"):
            entry = providers[direction]
            if entry["enabled"]:
                for _name, info in entry["providers"].items():
                    assert "registered" in info
                    assert "loaded" in info

    async def test_health_includes_engine_reachable_for_http_providers(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        providers = body["providers"]
        # If aivis_speech is configured, it should have engineReachable
        if providers.get("tts", {}).get("enabled"):
            tts_providers = providers["tts"].get("providers", {})
            if "aivis_speech" in tts_providers:
                aivis_info = tts_providers["aivis_speech"]
                assert "engineReachable" in aivis_info
                assert "baseUrl" in aivis_info
