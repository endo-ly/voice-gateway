"""Integration tests — acceptance criteria from plan.md §7.3."""

import base64
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAcceptanceHealth:
    async def test_health_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"


class TestAcceptanceModels:
    async def test_get_models_returns_data(self, client):
        resp = await client.get("/v1/models")
        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "list"
        assert len(body["data"]) >= 1

    async def test_model_tts_default_works(self, client):
        ids = [m["id"] for m in (await client.get("/v1/models")).json()["data"]]
        assert "tts-default" in ids


class TestAcceptanceVoices:
    async def test_get_voices_returns_data(self, client):
        resp = await client.get("/v1/voices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "list"
        assert len(body["data"]) >= 1

    async def test_voice_your_voice_name_works(self, client):
        ids = [v["id"] for v in (await client.get("/v1/voices")).json()["data"]]
        assert "your-voice-name" in ids


class TestAcceptanceOpenAISpeech:
    async def test_post_audio_speech_wav(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={"model": "tts-default", "voice": "your-voice-name", "input": "テスト"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.content.startswith(b"RIFF")

    async def test_unknown_model_404(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={"model": "nonexistent", "voice": "your-voice-name", "input": "x"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "model_not_found"

    async def test_unknown_voice_404(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={"model": "tts-default", "voice": "nonexistent", "input": "x"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "voice_not_found"

    async def test_voice_binding_missing_409(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={"model": "irodori-voicedesign", "voice": "your-voice-name", "input": "x"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "voice_binding_not_found"

    async def test_response_format_wav_only(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={"model": "tts-default", "voice": "your-voice-name", "input": "x", "response_format": "mp3"},
        )
        assert resp.status_code == 400

    async def test_speed_1_0_only(self, client):
        resp = await client.post(
            "/v1/audio/speech",
            json={"model": "tts-default", "voice": "your-voice-name", "input": "x", "speed": 2.0},
        )
        assert resp.status_code == 400


class TestAcceptanceNativeSpeech:
    async def test_post_native_speech_wav(self, client):
        resp = await client.post(
            "/v1/speech",
            json={"model": "tts-default", "voice_id": "your-voice-name", "speech_text": "了解"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.content.startswith(b"RIFF")

    async def test_native_speech_404_unknown_model(self, client):
        resp = await client.post(
            "/v1/speech",
            json={"model": "nonexistent", "voice_id": "your-voice-name", "speech_text": "x"},
        )
        assert resp.status_code == 404


class TestAcceptanceProviderExtensibility:
    def test_fake_provider_is_registered(self):
        from app.main import _provider_registry
        provider = _provider_registry.get("fake")
        assert provider.provider_name == "fake"

    def test_irodori_provider_is_registered(self):
        from app.main import _provider_registry
        provider = _provider_registry.get("irodori")
        assert provider.provider_name == "irodori"

    def test_registry_allows_additional_providers(self):
        from app.main import _provider_registry
        from app.infrastructure.providers.fake.provider import FakeProvider
        extra = FakeProvider()
        extra.provider_name = "qwen_tts"
        _provider_registry.register(extra)
        assert _provider_registry.get("qwen_tts").provider_name == "qwen_tts"


class TestAcceptanceYamlValidation:
    def test_models_yaml_loaded_with_safe_load(self):
        from app.main import _model_repo
        models = _model_repo.list_all()
        assert len(models) >= 1
        for m in models:
            assert m.id
            assert m.provider

    def test_voices_yaml_loaded_with_safe_load(self):
        from app.main import _voice_repo
        voices = _voice_repo.list_all()
        assert len(voices) >= 1
        for v in voices:
            assert v.voice_id
            assert v.display_name


def _parse_sse(text: str) -> list[dict]:
    events = []
    current_event = None
    current_data = None
    for line in text.strip().split("\n"):
        if line.startswith("event: "):
            current_event = line[len("event: "):]
        elif line.startswith("data: "):
            current_data = line[len("data: "):]
        elif line == "" and current_event is not None:
            events.append({"event": current_event, "data": current_data})
            current_event = None
            current_data = None
    if current_event is not None:
        events.append({"event": current_event, "data": current_data})
    return events


class TestAcceptanceSpeechStream:
    async def test_stream_returns_multiple_chunks_in_order(self, client):
        resp = await client.post(
            "/v1/speech/stream",
            json={
                "model": "tts-default",
                "voice_id": "your-voice-name",
                "speech_text": "一つ目の文です。二つ目の文です。三つ目の文です。",
                "segment": {"enabled": True, "mode": "conversation"},
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        events = _parse_sse(resp.text)
        audio_chunks = [e for e in events if e["event"] == "audio_chunk"]
        dones = [e for e in events if e["event"] == "done"]

        assert len(audio_chunks) >= 2, "should produce multiple chunks"

        for i, chunk in enumerate(audio_chunks):
            data = json.loads(chunk["data"])
            assert data["index"] == i, "chunks must be in index order"
            assert data["format"] == "wav"
            assert data["media_type"] == "audio/wav"
            base64.b64decode(data["audio_base64"])

        assert len(dones) == 1
        done_data = json.loads(dones[0]["data"])
        assert done_data["chunks"] == len(audio_chunks)

    async def test_stream_disabled_segment_single_chunk(self, client):
        resp = await client.post(
            "/v1/speech/stream",
            json={
                "model": "tts-default",
                "voice_id": "your-voice-name",
                "speech_text": "分割なしのテキストです。",
                "segment": {"enabled": False},
            },
        )
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        audio_chunks = [e for e in events if e["event"] == "audio_chunk"]
        assert len(audio_chunks) == 1

    async def test_stream_unknown_model_returns_error_event(self, client):
        resp = await client.post(
            "/v1/speech/stream",
            json={
                "model": "nonexistent",
                "voice_id": "your-voice-name",
                "speech_text": "テスト",
            },
        )
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        errors = [e for e in events if e["event"] == "error"]
        assert len(errors) >= 1
        error_data = json.loads(errors[0]["data"])
        assert "message" in error_data
        assert "code" in error_data

    async def test_stream_unknown_voice_returns_error_event(self, client):
        resp = await client.post(
            "/v1/speech/stream",
            json={
                "model": "tts-default",
                "voice_id": "nonexistent-voice",
                "speech_text": "テスト",
            },
        )
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        errors = [e for e in events if e["event"] == "error"]
        assert len(errors) >= 1

    async def test_stream_first_chunk_is_short(self, client):
        long_text = (
            "なるほど。それならまずIrodori-TTS-Serverを"
            "内部Engineとして扱うのがよいです。"
        )
        resp = await client.post(
            "/v1/speech/stream",
            json={
                "model": "tts-default",
                "voice_id": "your-voice-name",
                "speech_text": long_text,
                "segment": {"enabled": True, "mode": "conversation"},
            },
        )
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        audio_chunks = [e for e in events if e["event"] == "audio_chunk"]
        assert len(audio_chunks) >= 2

        first_data = json.loads(audio_chunks[0]["data"])
        assert first_data["text"] == "なるほど。"
