"""Tests for OpenAI-compatible speech route."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestOpenAISpeechRoute:
    async def test_post_audio_speech_returns_wav(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={
                "model": "tts-default",
                "voice": "your-voice-name",
                "input": "こんにちは",
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.content.startswith(b"RIFF")

    async def test_post_audio_speech_404_unknown_model(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={
                "model": "nonexistent",
                "voice": "your-voice-name",
                "input": "test",
            },
        )
        assert resp.status_code == 404

    async def test_post_audio_speech_404_unknown_voice(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={
                "model": "tts-default",
                "voice": "nonexistent",
                "input": "test",
            },
        )
        assert resp.status_code == 404

    async def test_post_audio_speech_409_voice_binding_missing(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={
                "model": "irodori-base",
                "voice": "your-voice-name",
                "input": "test",
            },
        )
        assert resp.status_code == 409

    async def test_post_audio_speech_400_invalid_format(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={
                "model": "tts-default",
                "voice": "your-voice-name",
                "input": "test",
                "response_format": "mp3",
            },
        )
        assert resp.status_code == 400
