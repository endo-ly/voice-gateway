"""Tests for SSE streaming via /v1/audio/speech with stream_format=sse."""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_speech_sse_returns_stream(client):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "tts-default",
            "voice": "your-voice-name",
            "input": "なるほど。それでは始めましょう。",
            "stream_format": "sse",
            "segment": {"enabled": True, "mode": "conversation"},
            "batch": {"max_concurrency": 1},
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    lines = response.text.strip().split("\n")
    events = _parse_sse(lines)

    audio_chunks = [e for e in events if e["event"] == "audio_chunk"]
    dones = [e for e in events if e["event"] == "done"]

    assert len(audio_chunks) >= 1
    assert len(dones) == 1

    for i, chunk in enumerate(audio_chunks):
        data = json.loads(chunk["data"])
        assert data["index"] == i
        assert data["format"] == "wav"
        assert data["media_type"] == "audio/wav"
        base64.b64decode(data["audio_base64"], validate=True)

    done_data = json.loads(dones[0]["data"])
    assert done_data["chunks"] == len(audio_chunks)


def test_speech_sse_disabled_segment(client):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "tts-default",
            "voice": "your-voice-name",
            "input": "これはテストです。",
            "stream_format": "sse",
            "segment": {"enabled": False},
        },
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    events = _parse_sse(lines)

    audio_chunks = [e for e in events if e["event"] == "audio_chunk"]
    assert len(audio_chunks) == 1

    data = json.loads(audio_chunks[0]["data"])
    assert data["text"] == "これはテストです。"


def test_speech_rejects_invalid_stream_format(client):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "tts-default",
            "voice": "your-voice-name",
            "input": "テスト",
            "stream_format": "websocket",
        },
    )

    assert response.status_code == 400
    body = json.loads(response.content)
    assert "stream_format" in body["error"]["message"]


def test_speech_without_stream_format_returns_binary(client):
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "tts-default",
            "voice": "your-voice-name",
            "input": "これはテストです。",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("audio/")


def _parse_sse(lines: list[str]) -> list[dict]:
    events = []
    current_event = None
    current_data = None

    for line in lines:
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
