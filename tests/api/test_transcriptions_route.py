"""Tests for native STT transcription route."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestTranscriptionsRoute:
    async def test_rejects_missing_file(self, client):
        resp = await client.post("/v1/transcribe")
        assert resp.status_code == 422

    async def test_latest_initially_null(self, client):
        resp = await client.get("/v1/transcriptions/latest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"] is None
