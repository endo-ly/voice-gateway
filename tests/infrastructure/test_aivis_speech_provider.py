import json

import httpx
import pytest

from app.domain.errors import InvalidProviderConfigError
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.infrastructure.providers.aivis_speech.constants import AIVIS_HEALTH_PATH
from app.infrastructure.providers.aivis_speech.provider import AivisSpeechProvider


@pytest.mark.asyncio
async def test_aivis_speech_provider_synthesizes_wav(monkeypatch):
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/audio_query":
            return httpx.Response(200, json={"speedScale": 1.0})
        if request.url.path == "/synthesis":
            return httpx.Response(200, content=b"RIFF....WAVE")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    provider = AivisSpeechProvider(base_url="http://aivis.local")
    result = await provider.synthesize(
        ProviderSynthesisRequest(
            model_id="aivis-default",
            voice_id="your-voice-name",
            text="こんにちは",
            provider="aivis_speech",
            engine="voicevox-compatible",
            provider_config={
                "speaker": 888753760,
                "output_sampling_rate": 24000,
                "output_stereo": False,
            },
        )
    )

    assert result.audio_bytes.startswith(b"RIFF")
    assert [request.url.path for request in requests] == ["/audio_query", "/synthesis"]
    assert requests[0].url.params["speaker"] == "888753760"
    synthesis_payload = json.loads(requests[1].content)
    assert synthesis_payload["outputSamplingRate"] == 24000
    assert synthesis_payload["outputStereo"] is False


@pytest.mark.asyncio
async def test_aivis_speech_provider_requires_integer_speaker():
    provider = AivisSpeechProvider()

    with pytest.raises(InvalidProviderConfigError):
        await provider.synthesize(
            ProviderSynthesisRequest(
                model_id="aivis-default",
                voice_id="your-voice-name",
                text="こんにちは",
                provider="aivis_speech",
                engine="voicevox-compatible",
                provider_config={},
            )
        )


@pytest.mark.asyncio
async def test_aivis_speech_health_returns_reachable_when_engine_responds():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == AIVIS_HEALTH_PATH:
            return httpx.Response(200, json={"version": "1.0.0"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    # We need to patch httpx.AsyncClient inside health()
    # health() creates its own client, so we patch at module level
    import unittest.mock
    with unittest.mock.patch.object(httpx, "AsyncClient", client_factory):
        provider = AivisSpeechProvider(base_url="http://aivis.local")
        result = await provider.health()

    assert result["engineReachable"] is True
    assert result["baseUrl"] == "http://aivis.local"


@pytest.mark.asyncio
async def test_aivis_speech_health_returns_unreachable_on_connection_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    import unittest.mock
    with unittest.mock.patch.object(httpx, "AsyncClient", client_factory):
        provider = AivisSpeechProvider(base_url="http://aivis.local")
        result = await provider.health()

    assert result["engineReachable"] is False
    assert result["baseUrl"] == "http://aivis.local"


@pytest.mark.asyncio
async def test_list_speakers_returns_raw_payload(monkeypatch):
    payload = [
        {
            "name": "まお",
            "speaker_uuid": "abc",
            "styles": [{"name": "ノーマル", "id": 888753760, "type": "talk"}],
        }
    ]

    captured_paths = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_paths.append(request.url.path)
        if request.url.path == "/speakers":
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    provider = AivisSpeechProvider(base_url="http://aivis.local")
    result = await provider.list_speakers()

    assert result == payload
    assert captured_paths == ["/speakers"]


@pytest.mark.asyncio
async def test_list_speakers_raises_provider_error_on_http_500(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    from app.domain.errors import ProviderExecutionError

    provider = AivisSpeechProvider(base_url="http://aivis.local")
    with pytest.raises(ProviderExecutionError):
        await provider.list_speakers()
