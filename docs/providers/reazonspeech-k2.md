# ReazonSpeech K2 Provider

Speech-to-Text provider using [ReazonSpeech K2](https://github.com/reazon-research/ReazonSpeech).

## Overview

- Provider name: `reazonspeech_k2`
- Direction: STT
- Call method: Python import (async wrapped via `asyncio.to_thread()`)
- Language: Japanese (default)

## Installation

```bash
uv sync --group dev --extra reazonspeech-k2
./scripts/install-reazonspeech-k2.sh
```

## Configuration

### models.yaml

```yaml
models:
  - id: stt-default
    direction: stt
    object: model
    display_name: ReazonSpeech K2 v2
    provider: reazonspeech_k2
    engine: k2
    defaults:
      language: ja
      max_audio_seconds: 30
      timeout_sec: 120
    provider_config:
      model_id: reazon-research/reazonspeech-k2-v2
```

> **Note**: `precision` and `device` settings are not yet supported by the
> provider. They are reserved for future use. Do not add them to
> `provider_config` — they will be silently ignored.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STT_VENDOR_DIR` | `.vendor` | ReazonSpeech installation directory |

## Audio Requirements

- Format: WAV (PCM)
- Default max duration: 30 seconds
- Default preferred sample rate: 16000 Hz
- Default preferred channels: 1 (mono)

## Limitations

- **Single model only**: The provider loads exactly one ReazonSpeech K2 model
  per process. If multiple `direction: stt` models are defined in `models.yaml`,
  only the first `reazonspeech_k2` entry is used for provider initialization.
  The API accepts `model` parameter, but all requests are processed by the same
  loaded model instance.
- **No runtime config switching**: `provider_config` values (e.g. `model_id`,
  `language`) are read at startup only. Per-request config overrides from
  `STTProfileResolver` are resolved but **not forwarded** to the provider at
  transcription time. Full `provider_config` propagation is planned for a
  future release.

## API Usage

### OpenAI-compatible

```bash
curl -X POST http://localhost:8012/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=stt-default"
```

Response:
```json
{"text": "転写されたテキスト"}
```

### Native

```bash
curl -X POST http://localhost:8012/v1/transcribe \
  -F "file=@audio.wav" \
  -F "model=stt-default" \
  -F "source=stackchan"
```

Response:
```json
{
  "ok": true,
  "data": {
    "text": "転写されたテキスト",
    "language": "ja",
    "durationSec": 5.234,
    "processingMs": 1200,
    "provider": "reazonspeech_k2",
    "model": "reazon-research/reazonspeech-k2-v2",
    "source": "stackchan",
    "audio": {
      "sampleRate": 16000,
      "channels": 1,
      "format": "wav"
    }
  }
}
```
