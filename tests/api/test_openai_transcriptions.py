"""Tests for OpenAI-compatible STT route."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestOpenAITranscriptions:
    async def test_rejects_missing_file(self, client):
        resp = await client.post("/v1/audio/transcriptions")
        assert resp.status_code == 422
