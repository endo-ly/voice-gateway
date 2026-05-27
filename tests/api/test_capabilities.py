"""Tests for capabilities route."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestCapabilities:
    async def test_capabilities_returns_200(self, client):
        resp = await client.get("/v1/capabilities")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["tts"]["enabled"], bool)
        assert isinstance(body["stt"]["enabled"], bool)
        assert isinstance(body["tts"]["providers"], list)
        assert isinstance(body["stt"]["providers"], list)
