"""Tests for IrodoriServerClient."""

import json
import os

import httpx
import pytest

from app.domain.errors import ProviderExecutionError, ProviderTimeoutError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.infrastructure.providers.irodori.server_client import IrodoriServerClient


def _make_request(**overrides) -> ProviderSynthesisRequest:
    defaults: dict = {
        "model_id": "tts-default",
        "voice_id": "egopulse",
        "text": "こんにちは",
        "provider": "irodori",
        "engine": "base",
        "provider_config": {
            "checkpoint": "Aratako/Irodori-TTS-500M-v2",
            "ref_wav_path": "/abs/path/to/ref.wav",
            "num_steps": 28,
            "seed": 42,
        },
    }
    defaults.update(overrides)
    return ProviderSynthesisRequest(**defaults)


@pytest.mark.asyncio
async def test_server_client_synthesizes_wav(monkeypatch):
    sent_payloads = []

    async def handler(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content))
        return httpx.Response(200, content=b"RIFF....WAVE")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    client = IrodoriServerClient(
        base_url="http://127.0.0.1:18790",
    )
    result = await client.synthesize(_make_request())

    assert result.audio_bytes.startswith(b"RIFF")
    assert result.media_type == "audio/wav"

    payload = sent_payloads[0]
    assert payload["model"] == "irodori-tts"
    assert payload["input"] == "こんにちは"
    assert payload["response_format"] == "wav"
    assert payload["irodori"]["chunking_enabled"] is False
    assert payload["irodori"]["ref_wav"] == os.path.abspath("/abs/path/to/ref.wav")
    assert payload["irodori"]["num_steps"] == 28
    assert payload["irodori"]["seed"] == 42


@pytest.mark.asyncio
async def test_server_client_uses_ref_latent(monkeypatch):
    sent_payloads = []

    async def handler(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content))
        return httpx.Response(200, content=b"RIFF....WAVE")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    client = IrodoriServerClient(base_url="http://127.0.0.1:18790")
    await client.synthesize(
        _make_request(
            provider_config={
                "checkpoint": "Aratako/Irodori-TTS-500M-v2",
                "ref_latent_path": "/abs/path/to/ref.pt",
                "num_steps": 28,
                "seed": 0,
            }
        )
    )

    payload = sent_payloads[0]
    assert payload["irodori"]["ref_latent"] == os.path.abspath("/abs/path/to/ref.pt")
    assert "ref_wav" not in payload["irodori"]


@pytest.mark.asyncio
async def test_server_client_strips_cli_only_keys(monkeypatch):
    sent_payloads = []

    async def handler(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(json.loads(request.content))
        return httpx.Response(200, content=b"RIFF....WAVE")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    client = IrodoriServerClient(base_url="http://127.0.0.1:18790")
    await client.synthesize(
        _make_request(
            provider_config={
                "checkpoint": "Aratako/Irodori-TTS-500M-v2",
                "ref_wav_path": "/abs/path/to/ref.wav",
                "model_device": "cuda",
                "codec_device": "cuda",
                "model_precision": "bf16",
                "codec_precision": "fp32",
                "num_steps": 28,
                "seed": 0,
            }
        )
    )

    irodori = sent_payloads[0]["irodori"]
    assert "checkpoint" not in irodori
    assert "model_device" not in irodori
    assert "codec_device" not in irodori
    assert "model_precision" not in irodori
    assert "codec_precision" not in irodori


@pytest.mark.asyncio
async def test_server_client_sends_api_key(monkeypatch):
    auth_headers = []

    async def handler(request: httpx.Request) -> httpx.Response:
        auth_headers.append(request.headers.get("authorization"))
        return httpx.Response(200, content=b"RIFF....WAVE")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    client = IrodoriServerClient(
        base_url="http://127.0.0.1:18790",
        api_key="secret-key",
    )
    await client.synthesize(_make_request())

    assert auth_headers[0] == "Bearer secret-key"


@pytest.mark.asyncio
async def test_server_client_raises_on_http_error(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    client = IrodoriServerClient(base_url="http://127.0.0.1:18790")
    with pytest.raises(ProviderExecutionError, match="HTTP 500"):
        await client.synthesize(_make_request())


@pytest.mark.asyncio
async def test_server_client_raises_on_empty_audio(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    client = IrodoriServerClient(base_url="http://127.0.0.1:18790")
    with pytest.raises(ProviderExecutionError, match="empty audio"):
        await client.synthesize(_make_request())


@pytest.mark.asyncio
async def test_server_client_raises_on_connection_error(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    client = IrodoriServerClient(base_url="http://127.0.0.1:18790")
    with pytest.raises(ProviderExecutionError):
        await client.synthesize(_make_request())
