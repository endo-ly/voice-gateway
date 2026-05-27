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

- **Model cache**: Models are lazily loaded on first use and cached by
  `model_id:language` key. Different `model_id` or `language` values in
  `provider_config` will trigger a new model load (expensive on first request).
  Subsequent requests with the same key reuse the cached model.
- **No model unloading**: Once loaded, models stay in memory for the process
  lifetime. There is no eviction or unloading mechanism.

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
