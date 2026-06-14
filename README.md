# voice-gateway

複数のTTS・STTエンジンを、OpenAI互換APIで統一的に扱うゲートウェイサーバー。

音声エンジンごとに異なるAPI形式や設定方法を吸収し、クライアント側はエンジンを意識せずに音声の入出力を行える。エージェントシステムや外部ツールから、同じAPIでTTS・STTを利用したい場合に使う。

## 特徴

- **Provider抽象化** — TTS・STTエンジンをAPIを変えずに差し替え可能
- **OpenAI互換API** — `/v1/audio/speech`, `/v1/audio/transcriptions` でOpenAIクライアントと互換
- **Native API** — 拡張パラメータを使える独自エンドポイント
- **YAMLプロファイル** — モデル・音声の設定をYAMLで管理
- **モード切替** — 1コードベースでTTS専用・STT専用・両対応を切り替え

## サーバーモード

`VOICE_GATEWAY_MODE` により起動する機能を切り替える。異なるマシンで同じコードベースを使い分けられる。

| モード | 登録されるルート | ユースケース |
|------|-------------|------------|
| `tts` | TTS系 + 共通 | GPU搭載WindowsマシンでIrodori等を動かす |
| `stt` | STT系 + 共通 | 軽量ミニPCでReazonSpeech等を動かす |
| `all` | 全ルート | 1台でTTS・STT両方を動かす |

## クイックスタート

### 1. インストール

```bash
git clone https://github.com/endo-ly/voice-gateway.git && cd voice-gateway
uv sync --group dev

# ReazonSpeech K2 (STT) を含む場合:
uv sync --group dev --extra reazonspeech-k2
./scripts/install-reazonspeech-k2.sh

# Irodori-TTS (TTS) を含む場合:
# server backend（デフォルト）:
./scripts/install-irodori-tts-server.sh    # Linux/macOS
./scripts/install-irodori-tts-server.ps1   # Windows
# CLI backend / ref_latentエンコードも必要な場合:
./scripts/install-irodori-tts.sh           # Linux/macOS
./scripts/install-irodori-tts.ps1          # Windows
```

### 2. 設定

テンプレートから設定ファイルを作成:

```bash
cp assets/models/models.example.yaml assets/models/models.yaml
cp assets/voices/your-voice-name/profile.example.yaml assets/voices/your-voice-name/profile.yaml
```

環境変数を設定（`.env` ファイルも可）:

```bash
# モード（デフォルト: all）
export VOICE_GATEWAY_MODE=all

# Irodori-TTS（TTS利用時）
export IRODORI_REPO_DIR=.vendor/Irodori-TTS

# Irodori-TTS-Serverを内部Engineとして管理起動する場合
export IRODORI_BACKEND=server
export IRODORI_MANAGE_SERVER=true
export IRODORI_SERVER_DIR=.vendor/Irodori-TTS-Server

# AivisSpeech（voice-gatewayからEngineも起動する場合）
export AIVIS_MANAGE_ENGINE=true
export AIVIS_ENGINE_DIR=.vendor/AivisSpeech-Engine
```

### 3. 起動

構成に応じて `--host` を使い分ける:

```bash
# 同じマシン内からのみアクセス（開発・ローカル利用）
uv run uvicorn app.main:app --host 127.0.0.1 --port 8012

# 別マシンからアクセス（全インターフェースにバインド）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8012

# 別マシンからアクセス（特定のインターフェースにバインド）
uv run uvicorn app.main:app --host 192.168.0.210 --port 8012
```

### 4. 動作確認

```bash
curl http://127.0.0.1:8012/health
# → {"status":"ok","providers":{"tts":{"registered":["irodori"],"loaded":["irodori"]},...}}
```

## 使い方

### TTS（音声合成）

**OpenAI互換:**

```bash
curl -X POST http://127.0.0.1:8012/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-default","voice":"your-voice-name","input":"こんにちは"}' \
  --output output.wav
```

**Native（拡張パラメータ）:**

```bash
curl -X POST http://127.0.0.1:8012/v1/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-default","voice_id":"your-voice-name","speech_text":"こんにちは"}' \
  --output output.wav
```

### Stream TTS（チャンク分割・SSE）

`stream_format: "sse"` を指定すると、テキストを発話チャンクに分割し、各チャンクの音声を順次SSEで返す。

```bash
curl -N -X POST http://127.0.0.1:8012/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-default",
    "voice": "your-voice-name",
    "input": "なるほど。それならまずIrodori-TTS-Serverを内部Engineとして扱うのがよいです。",
    "stream_format": "sse",
    "segment": {"enabled": true, "mode": "conversation"},
    "batch": {"max_concurrency": 1}
  }'
```

レスポンスは `text/event-stream`。各チャンクが `audio_chunk` イベントとして順次返り、最後に `done` イベントが返る。

```text
event: audio_chunk
data: {"index":0,"text":"なるほど。","tts_text":"なるほど。","format":"wav","media_type":"audio/wav","audio_base64":"..."}

event: audio_chunk
data: {"index":1,"text":"それならまず...","tts_text":"それならまず...","format":"wav","media_type":"audio/wav","audio_base64":"..."}

event: done
data: {"chunks":2}
```

チャンキングはprovider非依存でGateway側で行う。`segment.mode` に `conversation`（初回チャンク短め）または `narration`（長文向け）を指定できる。

### STT（音声認識）

**OpenAI互換:**

```bash
curl -X POST http://127.0.0.1:8012/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=stt-default"
# → {"text":"転写されたテキスト"}
```

**Native（拡張パラメータ）:**

```bash
curl -X POST http://127.0.0.1:8012/v1/transcribe \
  -F "file=@audio.wav" \
  -F "model=stt-default" \
  -F "source=stackchan"
```

**直近の転写結果:**

```bash
curl http://127.0.0.1:8012/v1/transcriptions/latest
```

### サーバー情報

```bash
# モード・Provider・Model一覧
curl http://127.0.0.1:8012/v1/capabilities

# Model一覧
curl http://127.0.0.1:8012/v1/models

# Voice一覧（tts/allモードのみ）
curl http://127.0.0.1:8012/v1/voices
```

## 環境変数

### 共通

| 変数 | デフォルト | 説明 |
|----------|---------|------|
| `VOICE_GATEWAY_MODE` | `all` | サーバーモード: `tts`, `stt`, `all` |
| `LOG_LEVEL` | `INFO` | ログレベル |
| `TIMEOUT_SEC` | `120` | Provider実行タイムアウト（秒） |
| `MAX_CONCURRENCY` | `1` | 同時実行数上限 |

### TTS

| 変数 | デフォルト | 説明 |
|----------|---------|------|
| `IRODORI_REPO_DIR` | `.vendor/Irodori-TTS` | Irodori-TTSリポジトリパス |
| `IRODORI_BACKEND` | `server` | Irodori backend: `server`（Irodori-TTS-Server経由）または `cli`（subprocess実行） |
| `IRODORI_MANAGE_SERVER` | `false` | `true` の場合、voice-gateway起動時にIrodori-TTS-Serverを起動する |
| `IRODORI_SERVER_BASE_URL` | `http://127.0.0.1:18790` | Irodori-TTS-ServerのURL |
| `IRODORI_SERVER_DIR` | `.vendor/Irodori-TTS-Server` | 管理起動するIrodori-TTS-Serverのディレクトリ |
| `IRODORI_SERVER_HOST` | `127.0.0.1` | Irodori-TTS-Server起動時のバインドホスト |
| `IRODORI_SERVER_PORT` | `18790` | Irodori-TTS-Server起動時のポート |
| `IRODORI_SERVER_STARTUP_TIMEOUT_SEC` | `300` | Irodori-TTS-Server起動待ちタイムアウト（秒） |
| `IRODORI_SERVER_API_KEY` | — | Irodori-TTS-Server側API keyを設定している場合に利用 |
| `AIVIS_BASE_URL` | `http://127.0.0.1:10101` | AivisSpeech EngineのURL |
| `AIVIS_MANAGE_ENGINE` | `false` | `true` の場合、voice-gateway起動時にAivisSpeech Engineも起動する |
| `AIVIS_ENGINE_DIR` | `.vendor/AivisSpeech-Engine` | 管理起動するAivisSpeech Engineのディレクトリ |
| `AIVIS_ENGINE_BIND_HOST` | — | Engine起動時のバインドホスト（未設定時は`AIVIS_BASE_URL`から抽出） |
| `AIVIS_ENGINE_PORT` | — | Engine起動時のポート（未設定時は`AIVIS_BASE_URL`から抽出） |
| `AIVIS_USE_GPU` | `false` | `true` の場合、Engine起動時に`--use_gpu`を使用する |
| `AIVIS_STARTUP_TIMEOUT_SEC` | `180` | AivisSpeech Engine起動待ちタイムアウト（秒） |

### STT

| 変数 | デフォルト | 説明 |
|----------|---------|------|
| `REAZONSPEECH_REPO_DIR` | `.vendor/ReazonSpeech` | ReazonSpeech リポジトリのclone先ルートパス（install script用） |
| `STT_CALLBACK_URL` | — | 転写完了時のコールバックURL |
| `STT_CALLBACK_TIMEOUT_MS` | `3000` | コールバックタイムアウト（ms） |

## APIエンドポイント

### 共通（全モード）

| メソッド | パス | 説明 |
|--------|----------|------|
| GET | `/health` | 死活監視 + Provider状態 |
| GET | `/v1/models` | Model一覧 |
| GET | `/v1/capabilities` | サーバー機能情報 |

### TTS（tts / all）

| メソッド | パス | 説明 |
|--------|----------|------|
| GET | `/v1/voices` | Voice一覧 |
| POST | `/v1/audio/speech` | OpenAI互換TTS（`stream_format: "sse"` でSSEストリーミング） |
| POST | `/v1/speech` | Native TTS |

### STT（stt / all）

| メソッド | パス | 説明 |
|--------|----------|------|
| POST | `/v1/audio/transcriptions` | OpenAI互換STT |
| POST | `/v1/transcribe` | Native STT |
| GET | `/v1/transcriptions/latest` | 直近の転写結果 |

## Provider対応

| Provider | 方向 | 呼び出し方式 | 動作環境 |
|----------|------|------------|---------|
| [Irodori-TTS](docs/providers/irodori.md) | TTS | server (HTTP) / CLI subprocess | Windows / Linux + GPU推奨 |
| [AivisSpeech Engine](docs/providers/aivis-speech.md) | TTS | HTTP API / managed process | managed: Linux / external: Linux / Windows |
| [ReazonSpeech K2](docs/providers/reazonspeech-k2.md) | STT | Python import | Linux |

## ドキュメント

| ドキュメント | 内容 |
|----------|------|
| [コンセプト](docs/CONCEPT.md) | 設計思想と使う理由 |
| [APIリファレンス](docs/api-reference.md) | 全エンドポイントの仕様 |
| [設定ガイド](docs/configuration.md) | 環境変数とYAMLプロファイル |
| [アーキテクチャ](docs/architecture.md) | 層構造とデータフロー |
| [拡張ガイド](docs/extension-guide.md) | Provider / Voice / Modelの追加手順 |
| [開発ガイド](docs/development.md) | 環境構築、テスト、プロジェクト構成 |

## License

[MIT](LICENSE)
