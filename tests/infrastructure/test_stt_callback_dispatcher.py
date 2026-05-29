import json

from app.domain.value_objects.transcription_result import TranscriptionResult
from app.infrastructure.events.stt_callback_dispatcher import dispatch_stt_callbacks


def test_dispatch_stt_callbacks_posts_bridge_shape(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b""

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.infrastructure.events.stt_callback_dispatcher.urlopen", fake_urlopen)

    warning = dispatch_stt_callbacks(
        TranscriptionResult(
            text="こんにちは",
            language="ja",
            duration_sec=1.25,
            processing_ms=321,
            provider="reazonspeech_k2",
            model="reazon-research/reazonspeech-k2-v2",
            source="stackchan",
            audio_info={"sampleRate": 16000, "channels": 1, "format": "wav"},
        ),
        "http://127.0.0.1:8787/stt/events",
        timeout_ms=2500,
    )

    assert warning is None
    assert captured["url"] == "http://127.0.0.1:8787/stt/events"
    assert captured["timeout"] == 2.5
    assert captured["body"] == {
        "source": "stackchan",
        "text": "こんにちは",
        "language": "ja",
        "durationSec": 1.25,
        "processingMs": 321,
        "provider": "reazonspeech_k2",
        "model": "reazon-research/reazonspeech-k2-v2",
        "audio": {"sampleRate": 16000, "channels": 1, "format": "wav"},
    }
