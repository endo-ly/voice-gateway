# voice-gateway

Unified voice gateway for STT and TTS with OpenAI-compatible API.

## Architecture

Clean Architecture / 4-layer (Handler → UseCase → Gateway → Provider).

Provider abstraction allows swapping TTS/STT engines without changing API contracts. YAML profiles manage model and voice configuration.

## Modes

| Mode | Description |
|------|-------------|
| `tts` | Text-to-Speech only |
| `stt` | Speech-to-Text only |
| `all` | Both TTS and STT (default) |

## Features

- **Provider abstraction** — Swap TTS/STT engines without API changes
- **YAML profiles** — Model and voice configuration via YAML files
- **OpenAI-compatible API** — Drop-in replacement for OpenAI TTS/STT endpoints
- **Native API** — Extended parameters for custom integrations

## Quick Start

### 1. Install

```bash
uv sync --group dev

# With ReazonSpeech K2 STT support:
uv sync --group dev --extra reazonspeech-k2
./scripts/install-reazonspeech-k2.sh
```

### 2. Configure

```bash
cp assets/models/models.example.yaml assets/models/models.yaml
cp assets/voices/your-voice-name/profile.example.yaml assets/voices/your-voice-name/profile.yaml
```

Set environment variables (or use `.env`):

```bash
export VOICE_GATEWAY_MODE=all
export IRODORI_REPO_DIR=/path/to/Irodori-TTS
```

### 3. Run

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8012
```

### 4. Verify

```bash
curl http://127.0.0.1:8012/health
# → {"status":"ok"}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VOICE_GATEWAY_MODE` | `all` | Server mode: `tts`, `stt`, or `all` |
| `IRODORI_REPO_DIR` | — | Irodori-TTS installation path |
| `STT_VENDOR_DIR` | `.vendor` | ReazonSpeech installation directory |

## API Endpoints

### TTS

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/audio/speech` | OpenAI-compatible TTS |
| POST | `/v1/speech` | Native TTS with extended params |

### STT

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/audio/transcriptions` | OpenAI-compatible transcription |
| POST | `/v1/transcribe` | Native transcription with extended params |

### General

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/v1/models` | List available models |
| GET | `/v1/voices` | List available voices |

## Provider Support

| Provider | Direction | Call Method |
|----------|-----------|-------------|
| [Irodori-TTS](docs/providers/irodori.md) | TTS | Subprocess (CLI) |
| [ReazonSpeech K2](docs/providers/reazonspeech-k2.md) | STT | Python import |

## Documentation

| Document | Description |
|----------|-------------|
| [CONCEPT](docs/CONCEPT.md) | Design philosophy |
| [API Reference](docs/api-reference.md) | Endpoint specifications |
| [Configuration](docs/configuration.md) | Environment variables and profiles |
| [Architecture](docs/architecture.md) | Layer separation and data flow |
| [Extension Guide](docs/extension-guide.md) | Adding providers, voices, models |
| [Development](docs/development.md) | Setup, testing, project structure |

## License

[MIT](LICENSE)
