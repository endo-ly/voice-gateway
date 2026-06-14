# APIリファレンス

voice-gatewayが提供する全エンドポイントの仕様。

利用可能なエンドポイントは `VOICE_GATEWAY_MODE` により変動する（[設定ガイド](configuration.md)参照）。

## 目次

1. [エンドポイント一覧](#エンドポイント一覧)
2. [共通](#共通)
3. [TTS](#tts)
4. [STT](#stt)
5. [プロバイダー対応状況](#プロバイダー対応状況)

---

## エンドポイント一覧

### 共通（全モードで利用可能）

| メソッド | パス | 用途 |
|---------|------|------|
| `GET` | `/health` | 死活監視 |
| `GET` | `/v1/models` | model一覧取得 |
| `GET` | `/v1/capabilities` | サーバーの機能情報取得 |

### TTS（`tts` / `all` モード）

| メソッド | パス | 用途 |
|---------|------|------|
| `GET` | `/v1/voices` | voice一覧取得 |
| `POST` | `/v1/audio/speech` | OpenAI互換TTS |
| `POST` | `/v1/speech` | Native TTS |

### STT（`stt` / `all` モード）

| メソッド | パス | 用途 |
|---------|------|------|
| `POST` | `/v1/audio/transcriptions` | OpenAI互換STT |
| `POST` | `/v1/transcribe` | Native STT |
| `GET` | `/v1/transcriptions/latest` | 直近の転写結果取得 |

---

## 共通

### GET /health

サーバーの死活確認。登録済みProviderの状態も返す。

#### Response

```json
{
  "status": "ok",
  "providers": {
    "tts": {
      "registered": ["irodori"],
      "loaded": ["irodori"]
    },
    "stt": {
      "registered": ["reazonspeech_k2"],
      "loaded": ["reazonspeech_k2"]
    }
  }
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `status` | string | 常に `"ok"` |
| `providers.tts.registered` | string[] | 登録済みTTS Provider名 |
| `providers.tts.loaded` | string[] | ロード済みTTS Provider名 |
| `providers.stt.registered` | string[] | 登録済みSTT Provider名 |
| `providers.stt.loaded` | string[] | ロード済みSTT Provider名 |

`registered` は `models.yaml` に定義されているProvider。`loaded` は実際に初期化され利用可能なProvider。非モードの方向は空配列になる。

---

### GET /v1/models

利用可能なmodel一覧を返す。

#### Response

```json
{
  "object": "list",
  "data": [
    {
      "id": "tts-default",
      "object": "model",
      "display_name": "Default TTS"
    },
    {
      "id": "stt-default",
      "object": "model",
      "display_name": "ReazonSpeech K2 v2"
    }
  ]
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `object` | string | 常に `"list"` |
| `data[].id` | string | model識別子 |
| `data[].object` | string | 常に `"model"` |
| `data[].display_name` | string | 表示名 |

---

### GET /v1/capabilities

サーバーの機能・設定情報を返す。全モードで利用可能。

#### Response

```json
{
  "mode": "all",
  "tts": {
    "providers": ["irodori"],
    "models": ["tts-default"]
  },
  "stt": {
    "providers": ["reazonspeech_k2"],
    "models": ["stt-default"]
  }
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `mode` | string | 現在のサーバーモード（`tts` / `stt` / `all`） |
| `tts.providers` | string[] | 登録済みTTS Provider名 |
| `tts.models` | string[] | TTS model ID一覧 |
| `stt.providers` | string[] | 登録済みSTT Provider名 |
| `stt.models` | string[] | STT model ID一覧 |

---

## TTS

### GET /v1/voices

利用可能なvoice一覧を返す。voice-gateway独自の運用補助API。

#### Response

```json
{
  "object": "list",
  "data": [
    {
      "id": "your-voice-name",
      "object": "voice",
      "display_name": "your-voice-name",
      "preferred_model": "tts-default"
    }
  ]
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `data[].id` | string | voice識別子 |
| `data[].object` | string | 常に `"voice"` |
| `data[].display_name` | string | 表示名 |
| `data[].preferred_model` | string | 推奨model ID |

---

### POST /v1/audio/speech

OpenAI互換クライアント向けのTTS API。完全互換ではなく、必要最小限のsubset。
`stream_format` パラメータでSSEストリーミング（チャンク分割配信）に切り替え可能。

#### Request

**通常（binary WAV）:**

```json
{
  "model": "tts-default",
  "voice": "your-voice-name",
  "input": "こんにちは。今日は静かに話します。"
}
```

**SSEストリーミング:**

```json
{
  "model": "tts-default",
  "voice": "your-voice-name",
  "input": "なるほど。それでは始めましょう。長文の場合はチャンクに分割されます。",
  "stream_format": "sse",
  "segment": {"enabled": true, "mode": "conversation"},
  "batch": {"max_concurrency": 1, "stop_on_error": true}
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `model` | string | **Yes** | model ID |
| `voice` | string | **Yes** | voice ID |
| `input` | string | **Yes** | 読み上げテキスト。空文字不可 |
| `response_format` | string | No | v0では `wav` のみ。省略時 `"wav"` |
| `speed` | float | No | v0では `1.0` のみ。省略時 `1.0` |
| `stream_format` | string \| null | No | `"sse"` を指定するとSSEストリーミング。省略時 `null`（binary） |
| `segment.enabled` | bool | No | テキスト分割の有効/無効。省略時 `true`。SSE時のみ意味を持つ |
| `segment.mode` | string | No | `"conversation"`（初回チャンク短め）または `"narration"`（長文向け）。省略時 `"conversation"` |
| `batch.max_concurrency` | int | No | チャンク並列合成数（`>=1`）。省略時 `1`（順次） |
| `batch.ordered` | bool | No | 結果を入力順に返す。省略時 `true` |
| `batch.stop_on_error` | bool | No | エラー時にストリームを打ち切る。省略時 `true` |
| `extra_options` | object | No | Provider固有の追加オプション。省略時 `{}` |

> **Note**: OpenAI APIの `instructions` はv0未対応。送信するとバリデーションエラーになる。
> `stream_format` は `"sse"` 以外の値を指定すると400エラーになる。

#### Response — binary（`stream_format` 省略時）

```
Status: 200
Content-Type: audio/wav
Body: WAVバイナリ
```

#### Response — SSE（`stream_format: "sse"` 時）

```
Status: 200
Content-Type: text/event-stream; charset=utf-8
```

```text
event: audio_chunk
data: {"index":0,"text":"なるほど。","tts_text":"なるほど。","format":"wav","media_type":"audio/wav","audio_base64":"UklGRi..."}

event: audio_chunk
data: {"index":1,"text":"それでは始めましょう。","tts_text":"それでは始めましょう。","format":"wav","media_type":"audio/wav","audio_base64":"UklGRi..."}

event: done
data: {"chunks":2}
```

| SSEイベント | 説明 |
|------------|------|
| `audio_chunk` | 1チャンクの音声（base64エンコードWAV）。クライアント側でデコードが必要 |
| `done` | 全チャンク配信完了。`chunks` に総チャンク数 |
| `error` | エラー発生。`message` と `code` を含む。`stop_on_error=false` の場合は配信継続 |

#### Response (エラー)

| ステータス | code | 発生条件 |
|-----------|------|---------|
| 400 | `unsupported_response_format` | `response_format` が `wav` 以外 |
| 400 | `unsupported_speed` | `speed` が `1.0` 以外 |
| 400 | — | `stream_format` が `"sse"` 以外の値 |
| 404 | `model_not_found` | 存在しない `model` |
| 404 | `voice_not_found` | 存在しない `voice` |
| 409 | `voice_binding_not_found` | voiceは存在するが、指定modelのbindingがない |
| 500 | `provider_execution_error` | Provider実行失敗 |
| 504 | `provider_timeout` | Provider timeout |

エラー形式（binary時）:

```json
{
  "error": {
    "message": "Model not found: unknown",
    "type": "invalid_request_error",
    "param": "model",
    "code": "model_not_found"
  }
}
```

SSE時のエラーは `event: error` としてストリーム内に配信される（HTTPステータスは200）。

---

### POST /v1/speech

自作エージェント向けのNative TTS API。OpenAI互換に縛られない拡張パラメータを利用できる。

#### Request

```json
{
  "model": "tts-default",
  "voice_id": "your-voice-name",
  "speech_text": "了解しました。今から調べます。"
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `model` | string | **Yes** | model ID |
| `voice_id` | string | **Yes** | voice ID |
| `speech_text` | string | **Yes** | 読み上げテキスト。空文字不可。Irodoriでは絵文字によるスタイル制御に対応 |
| `response_format` | string | No | v0では `wav` のみ。省略時 `"wav"` |
| `style_hints` | object | No | **予約**。将来Providerが解釈可能な補助情報。v0では未使用。省略時 `null` |

#### Response

`POST /v1/audio/speech` と同じ。

---

## STT

### POST /v1/audio/transcriptions

OpenAI互換クライアント向けのSTT API。multipart/form-dataで音声ファイルをアップロードする。

#### Request

```
Content-Type: multipart/form-data

file: audio.wav (WAVファイル)
model: stt-default
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `file` | file | **Yes** | 音声ファイル（WAV/PCM） |
| `model` | string | **Yes** | model ID |
| `response_format` | string | No | `"json"` (default) または `"text"` |

#### Response (成功)

`response_format=json` (default):

```json
{"text": "転写されたテキスト"}
```

`response_format=text`:

```
Status: 200
Content-Type: text/plain; charset=utf-8
Body: 転写されたテキスト
```

#### Response (エラー)

| ステータス | code | 発生条件 |
|-----------|------|---------|
| 400 | `audio_validation_error` | 音声ファイルの形式不正 |
| 400 | `audio_too_large` | ファイルサイズ超過 |
| 400 | `audio_too_long` | 音声長超過 |
| 404 | `model_not_found` | 存在しない `model` |
| 500 | `transcription_failed` | Provider実行失敗 |
| 503 | `model_not_loaded` | モデル未ロード |

---

### POST /v1/transcribe

自作エージェント向けのNative STT API。拡張パラメータを利用できる。

#### Request

```
Content-Type: multipart/form-data

file: audio.wav
model: stt-default
source: stackchan
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `file` | file | **Yes** | 音声ファイル（WAV/PCM） |
| `model` | string | **Yes** | model ID |
| `source` | string | No | 音声ソース識別子（デバイス名等）。省略時 `null` |

#### Response (成功)

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

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `ok` | bool | 常に `true` |
| `data.text` | string | 転写テキスト |
| `data.language` | string | 検出言語 |
| `data.durationSec` | float | 音声の長さ（秒） |
| `data.processingMs` | int | 処理時間（ミリ秒） |
| `data.provider` | string | 使用したProvider名 |
| `data.model` | string | 使用したモデルID |
| `data.source` | string | リクエストのsource値 |
| `data.audio` | object | 音声メタデータ |

---

### GET /v1/transcriptions/latest

直近の転写結果を取得する。

#### Response (成功)

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
  },
  "timestamp": "2026-01-15T10:30:00.123456+09:00"
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `timestamp` | string | 転写時刻（ISO 8601） |
| その他 | — | `POST /v1/transcribe` の `data` と同じ |

#### Response (データなし)

```
Status: 200
```

```json
{"ok": true, "data": null, "timestamp": null}
```

---

## プロバイダー対応状況

### TTS

#### POST /v1/audio/speech

| パラメータ | Irodori (base) | Irodori (voicedesign) |
|-----------|---------------|----------------------|
| `model` | ✅ ModelProfile解決に使用 | ✅ ModelProfile解決に使用 |
| `voice` | ✅ VoiceProfile解決に使用 | ✅ VoiceProfile解決に使用 |
| `input` | ✅ `--text` に渡す | ✅ `--text` に渡す |
| `response_format` | `wav` のみ対応 | `wav` のみ対応 |
| `speed` | `1.0` のみ対応 | `1.0` のみ対応 |
| `stream_format` | ✅ `"sse"` でチャンク分割SSE配信 | ✅ `"sse"` でチャンク分割SSE配信 |
| `segment` | ✅ Gateway側でテキスト分割制御 | ✅ Gateway側でテキスト分割制御 |
| `batch` | ✅ `max_concurrency` / `stop_on_error` 適用 | ✅ `max_concurrency` / `stop_on_error` 適用 |

#### POST /v1/speech

| パラメータ | Irodori (base) | Irodori (voicedesign) |
|-----------|---------------|----------------------|
| `model` | ✅ ModelProfile解決に使用 | ✅ ModelProfile解決に使用 |
| `voice_id` | ✅ VoiceProfile解決に使用 | ✅ VoiceProfile解決に使用 |
| `speech_text` | ✅ `--text` に渡す | ✅ `--text` に渡す |
| `response_format` | `wav` のみ対応 | `wav` のみ対応 |
| `style_hints` | ⏭ v0では未使用（将来: Providerが解釈） | ⏭ v0では未使用（将来: Providerが解釈） |

#### YAML設定経由のIrodori固有パラメータ

APIのリクエストパラメータではなく、YAMLプロファイルの `provider_config` で制御する設定。

| 設定キー | engine | 出処 | Irodori CLI引数 |
|---------|--------|------|----------------|
| `checkpoint` | base / voicedesign | ModelProfile | `--hf-checkpoint` |
| `model_device` | base / voicedesign | ModelProfile | `--model-device` |
| `codec_device` | base / voicedesign | ModelProfile | `--codec-device` |
| `model_precision` | base / voicedesign | ModelProfile | `--model-precision` |
| `codec_precision` | base / voicedesign | ModelProfile | `--codec-precision` |
| `ref_latent_path` | base | VoiceBinding | `--ref-latent` |
| `ref_wav_path` | base | VoiceBinding | `--ref-wav` |
| `caption` | voicedesign | VoiceBinding | `--caption` |
| `num_steps` | base / voicedesign | VoiceBinding | `--num-steps` |
| `seed` | base / voicedesign | VoiceBinding | `--seed` |
| `max_text_len` | base / voicedesign | ModelProfile / VoiceBinding | `--max-text-len` |
| `max_caption_len` | base / voicedesign | ModelProfile / VoiceBinding | `--max-caption-len` |
| `speaker_kv_scale` | base | VoiceBinding | `--speaker-kv-scale` |

> 詳細は [Provider: Irodori](providers/irodori.md) を参照。

### STT

#### POST /v1/audio/transcriptions

| パラメータ | ReazonSpeech K2 |
|-----------|----------------|
| `file` | ✅ audio_validator検証 → 推論に渡す |
| `model` | ✅ ModelProfile解決に使用 |
| `response_format` | `json` / `text` に対応 |

#### POST /v1/transcribe

| パラメータ | ReazonSpeech K2 |
|-----------|----------------|
| `file` | ✅ audio_validator検証 → 推論に渡す |
| `model` | ✅ ModelProfile解決に使用 |
| `source` | ✅ レスポンスにそのまま含める |

#### YAML設定経由のReazonSpeech K2固有パラメータ

| 設定キー | 出処 | 説明 |
|---------|------|------|
| `model_id` | ModelProfile.provider_config | HuggingFaceモデルID（キャッシュキーに使用） |
| `language` | ModelProfile.defaults | 言語コード（デフォルト: `ja`） |
| `max_audio_seconds` | ModelProfile.defaults | 最大音声長（秒、デフォルト: 30） |

> 詳細は [Provider: ReazonSpeech K2](providers/reazonspeech-k2.md) を参照。
