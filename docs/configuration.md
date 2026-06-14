# 設定ガイド

voice-gatewayの全設定項目と、プロファイルの書き方を説明する。

## 目次

1. [環境変数](#環境変数)
2. [サーバーモード](#サーバーモード)
3. [Model Profile](#model-profile)
4. [Voice Profile](#voice-profile)
5. [設定マージ規則](#設定マージ規則)
6. [ファイル配置](#ファイル配置)

---

## 環境変数

### 共通

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `VOICE_GATEWAY_MODE` | No | `all` | サーバーモード。`tts` / `stt` / `all`（[詳細](#サーバーモード)） |
| `PROJECT_ROOT` | No | voice-gatewayのリポジトリルート | 相対パス解決の基準ディレクトリ |
| `LOG_LEVEL` | No | `INFO` | アプリケーションログレベル。生成内容の切り分け時は `DEBUG` にすると、Irodoriへ渡した入力・参照ファイル・stdout/stderrを確認できる |
| `ASSETS_DIR` | No | `assets` | プロファイル配置ディレクトリ。相対パスは `PROJECT_ROOT` 基準 |
| `TMP_DIR` | No | `tmp` | 一時ファイル出力ディレクトリ。相対パスは `PROJECT_ROOT` 基準 |
| `TIMEOUT_SEC` | No | `120` | Provider実行タイムアウト（秒） |
| `MAX_CONCURRENCY` | No | `1` | 同時生成数上限 |

### TTS（Irodori）

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `IRODORI_BACKEND` | No | `server` | `server`（Irodori-TTS-Server経由）または `cli`（subprocess実行） |
| `IRODORI_REPO_DIR` | ※cli | `.vendor/Irodori-TTS` | [Irodori-TTS](https://github.com/Aratako/Irodori-TTS) リポジトリパス。`cli` backendで使用。`uv run --no-sync python infer.py` を実行 |
| `IRODORI_SERVER_DIR` | ※server | `.vendor/Irodori-TTS-Server` | [Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server) リポジトリパス。`server` backendの管理起動で使用 |
| `IRODORI_MANAGE_SERVER` | No | `false` | `true` の場合、voice-gateway起動時にIrodori-TTS-Serverをsubprocess起動する |
| `IRODORI_SERVER_BASE_URL` | No | `http://127.0.0.1:18790` | Irodori-TTS-ServerのURL（管理起動・外部起動どちらでも共通） |
| `IRODORI_SERVER_HOST` | No | `127.0.0.1` | 管理起動時のIrodori-TTS-Server listen host |
| `IRODORI_SERVER_PORT` | No | `18790` | 管理起動時のIrodori-TTS-Server listen port |
| `IRODORI_SERVER_STARTUP_TIMEOUT_SEC` | No | `300` | Irodori-TTS-Server起動待ちタイムアウト（秒） |
| `IRODORI_SERVER_API_KEY` | No | なし | Irodori-TTS-ServerのAPIキー（サーバー側で設定している場合） |

> ※ `IRODORI_REPO_DIR` は `IRODORI_BACKEND=cli` の場合のみ必須。`IRODORI_SERVER_DIR` は `IRODORI_MANAGE_SERVER=true` の場合のみ必須。`server` backend（デフォルト）で外部起動のIrodori-TTS-Serverを使う場合はどちらも不要。

> **Note**: `engine: voicedesign` は `IRODORI_BACKEND=cli` でのみ使用可能。`server` backend では `InvalidProviderConfigError` になる。

### STT（ReazonSpeech）

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `REAZONSPEECH_REPO_DIR` | No | `.vendor/ReazonSpeech` | ReazonSpeech リポジトリのclone先ルートパス。`scripts/install-reazonspeech-k2.sh` がこのディレクトリをclone/pullし、`pkg/k2-asr` を voice-gateway の `.venv` にinstallする |
| `STT_CALLBACK_URL` | No | なし | 転写完了時のコールバックURL。`http://` または `https://` のみ対応 |
| `STT_CALLBACK_TIMEOUT_MS` | No | `3000` | コールバック送信のタイムアウト（ミリ秒）。正の整数のみ |

`.env` ファイルも利用可能（`.env.example` をコピーして使用）。Windowsパスはバックスラッシュのエスケープを避けるため、`IRODORI_REPO_DIR='C:\svc\runtimes\Irodori-TTS'` のようにシングルクォートで書くか、`C:/svc/runtimes/Irodori-TTS` のように `/` を使う。

---

## サーバーモード

`VOICE_GATEWAY_MODE` により、起動する機能を切り替える。

| モード | 登録されるルート | 必要な環境変数 |
|--------|----------------|--------------|
| `tts` | TTS系 + 共通 | `IRODORI_REPO_DIR` (cli backend時) / `IRODORI_SERVER_DIR` (server管理起動時) |
| `stt` | STT系 + 共通 | — |
| `all` | 全ルート | `IRODORI_REPO_DIR` (cli backend時) / `IRODORI_SERVER_DIR` (server管理起動時) |

共通ルート（`/health`, `/v1/models`, `/v1/capabilities`）は全モードで利用可能。

---

## Model Profile

modelは、クライアントが指定するルートIDである。どのProvider・engineを使うかはこのProfile側を正とする。

### 配置場所

```
assets/models/models.yaml
```

テンプレート: `assets/models/models.example.yaml`

### スキーマ

```yaml
models:
  - id: string              # 必須: model識別子
    direction: string       # 必須: "tts" または "stt"
    object: model           # 固定値
    display_name: string    # 必須: 表示名
    provider: string        # 必須: Provider名 (irodori, reazonspeech_k2, fake 等)
    engine: string          # 必須: engine名 (base, voicedesign, k2 等)
    defaults: {}            # 省略可: デフォルト値（directionにより異なる）
    provider_config: {}     # 省略可: Provider固有設定
```

`direction` により `defaults` のスキーマが変わる:

- `direction: tts` → `TTSModelDefaults`（response_format, speed, timeout_sec）
- `direction: stt` → `STTModelDefaults`（language, max_audio_seconds, timeout_sec）

### 例

```yaml
models:
  # TTS
  - id: tts-default
    direction: tts
    object: model
    display_name: Default TTS
    provider: irodori
    engine: base
    defaults:
      response_format: wav
      speed: 1.0
      timeout_sec: 120
    provider_config:
      checkpoint: Aratako/Irodori-TTS-500M-v2
      model_device: cuda
      codec_device: cuda
      model_precision: fp32
      codec_precision: fp32

  # STT
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

  # AivisSpeech TTS
  - id: aivis-default
    direction: tts
    object: model
    display_name: AivisSpeech Engine
    provider: aivis_speech
    engine: voicevox-compatible
    defaults:
      response_format: wav
      speed: 1.0
      timeout_sec: 120
    provider_config:
      speaker: 888753760
      output_sampling_rate: 24000
      output_stereo: false

  # テスト用
  - id: tts-fake
    direction: tts
    object: model
    display_name: Fake TTS (for testing)
    provider: fake
    engine: base
```

### provider_configの内容

`provider_config` の中身はProviderごとに異なる。Application層は中身を解釈せず、Providerにそのまま渡す。

#### Irodori (engine: base)

| キー | 型 | 説明 |
|------|-----|------|
| `checkpoint` | string | HuggingFace checkpoint名 |
| `model_device` | string | `cuda` または `cpu` |
| `codec_device` | string | `cuda` または `cpu` |
| `model_precision` | string | `bf16` または `fp32` |
| `codec_precision` | string | `bf16` または `fp32` |
| `max_text_len` | integer | 省略可。Irodoriの `--max-text-len` に渡す最大テキストトークン長 |
| `max_caption_len` | integer | 省略可。Irodoriの `--max-caption-len` に渡す最大キャプショントークン長 |

#### ReazonSpeech K2 (engine: k2)

| キー | 型 | 説明 |
|------|-----|------|
| `model_id` | string | HuggingFaceモデルID。キャッシュキーに使用（`model_id:language`） |

> `precision` と `device` は未対応。予約済み。

#### AivisSpeech (engine: voicevox-compatible)

| キー | 型 | 説明 |
|------|-----|------|
| `speaker` | integer | AivisSpeech Engineのspeaker/style ID |
| `speaker_id` | integer | `speaker` の別名。`speaker` が優先される |
| `output_sampling_rate` | integer | 省略可。AivisSpeechの `outputSamplingRate` に反映 |
| `output_stereo` | boolean | 省略可。AivisSpeechの `outputStereo` に反映 |

Engineの接続先と管理起動は環境変数で制御する。

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `AIVIS_BASE_URL` | `http://127.0.0.1:10101` | AivisSpeech EngineのURL |
| `AIVIS_MANAGE_ENGINE` | `false` | `true` の場合、voice-gateway起動時にAivisSpeech Engineも起動する |
| `AIVIS_ENGINE_DIR` | `.vendor/AivisSpeech-Engine` | 管理起動するAivisSpeech Engineのディレクトリ |
| `AIVIS_STARTUP_TIMEOUT_SEC` | `180` | AivisSpeech Engine起動待ちタイムアウト（秒） |

#### Fake

設定不要。`provider_config: {}` でよい。

---

## Voice Profile

voiceは、論理的な声・人格IDである。特定のProviderに固定されない。TTSでのみ使用される。

### 配置場所

```
assets/voices/<voice_id>/profile.yaml
```

テンプレート: `assets/voices/<voice_id>/profile.example.yaml`

### スキーマ

```yaml
voice_id: string            # 必須: voice識別子（ディレクトリ名と一致させる）
display_name: string        # 必須: 表示名
description: string         # 省略可: 説明

defaults:                   # 省略可: デフォルト値
  preferred_model: tts-default
  response_format: wav
  speed: 1.0

bindings:                   # model_idごとの設定
  <model_id>:               # どのmodelから呼ばれるか
    provider_config: {}     # そのmodel用のProvider固有設定
```

### 例

```yaml
voice_id: your-voice-name
display_name: your-voice-name
description: 静かで知的、近い距離感の男性声

defaults:
  preferred_model: tts-default
  response_format: wav
  speed: 1.0

bindings:
  tts-default:
    provider_config:
      ref_wav_path: assets/voices/your-voice-name/ref.wav
      seed: 42
      num_steps: 28
      speaker_kv_scale: 1.1

  irodori-voicedesign:
    provider_config:
      caption: 20代前半の男性。落ち着いていて知的だがやわらかい。距離感は近め。
      seed: 42
      num_steps: 28
```

### bindingsのキーについて

`bindings` のキーは `model_id` である。クライアントが指定した `model` と一致するキーが存在しない場合、409エラーとなる。

### VoiceProfileにProviderを書かない理由

`provider` と `engine` はModelProfile側が正である。VoiceProfile側には重複して持たせない。VoiceProfileは「このvoiceをどう実現するか」のprovider_configだけを持つ。

### Irodori voice固有のprovider_config

#### engine: base

| キー | 型 | 説明 |
|------|-----|------|
| `ref_latent_path` | string | 参照音声のlatentファイルパス（優先） |
| `ref_wav_path` | string | 参照音声のWAVファイルパス（`ref_latent_path` がない場合に使用） |
| `seed` | int | 乱数シード |
| `num_steps` | int | 生成ステップ数 |
| `speaker_kv_scale` | float | 話者スケール |

`ref_latent_path` と `ref_wav_path` はどちらか一方が必須。両方ある場合は `ref_latent_path` が優先される。

#### engine: voicedesign

> **制限**: `IRODORI_BACKEND=cli` でのみ使用可能。`server` backendでは拒否される。

| キー | 型 | 説明 |
|------|-----|------|
| `caption` | string | 声のキャプション（テキスト記述） |
| `seed` | int | 乱数シード |
| `num_steps` | int | 生成ステップ数 |

---

## 設定マージ規則

### TTS

音声生成時の最終設定は、次の5層を順にマージして決まる。後の層が前の層を上書きする。

```
1. ModelProfile.defaults (TTSModelDefaults)  （最も優先度が低い）
2. VoiceProfile.defaults
3. ModelProfile.provider_config
4. VoiceProfile.bindings[model].provider_config
5. request options                            （最も優先度が高い）
```

#### マージ例

クライアントが `model=tts-default, voice=your-voice-name` でリクエストした場合:

```
1. ModelDefaults:     {response_format: wav, speed: 1.0, timeout_sec: 120}
2. VoiceDefaults:     {preferred_model: tts-default, response_format: wav, speed: 1.0}
3. Model provider:    {checkpoint: ..., model_device: cuda, codec_device: cuda, ...}
4. Voice binding:     {ref_wav_path: ..., seed: 42, num_steps: 28, speaker_kv_scale: 1.1}
5. Request:           {}
```

最終的にProviderに渡る設定:

```yaml
checkpoint: Aratako/Irodori-TTS-500M-v2
model_device: cuda
codec_device: cuda
model_precision: fp32
codec_precision: fp32
ref_wav_path: assets/voices/your-voice-name/ref.wav
seed: 42
num_steps: 28
speaker_kv_scale: 1.1
response_format: wav
speed: 1.0
timeout_sec: 120
```

### STT

STTではVoiceProfileを使用しないため、3層のマージになる。

```
1. ModelProfile.defaults (STTModelDefaults)   （最も優先度が低い）
2. ModelProfile.provider_config
3. request options                            （最も優先度が高い）
```

---

## ファイル配置

```
assets/
  models/
    models.example.yaml    ← テンプレート（コミット対象）
    models.yaml            ← 実際の設定（.gitignore対象）
  voices/
    your-voice-name/
      profile.example.yaml ← テンプレート
      profile.yaml         ← 実際の設定
      ref.wav              ← 参照音声（.gitignore対象）
      ref_latent.pt        ← バイオナリ（.gitignore対象）
```
