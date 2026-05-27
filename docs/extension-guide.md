# 拡張ガイド

voice-gatewayに新しいProvider、Voice、Modelを追加する手順。

## 目次

1. [共通の前提](#共通の前提)
2. [TTS Providerの追加](#tts-providerの追加)
3. [STT Providerの追加](#stt-providerの追加)
4. [Voiceの追加](#voiceの追加)
5. [Modelの追加](#modelの追加)
6. [拡張チェックリスト](#拡張チェックリスト)

---

## 共通の前提

### direction

Modelには `direction` フィールド（`"tts"` または `"stt"`）が必須。これにより:

- `defaults` のスキーマが切り替わる（`TTSModelDefaults` / `STTModelDefaults`）
- モード分岐でどのRegistryに登録されるかが決まる
- API層でルートが有効になるかが決まる

### Provider Protocols

| 方向 | Protocol | メソッド |
|------|----------|---------|
| TTS | `TTSProvider` | `async def synthesize(request: ProviderSynthesisRequest) -> SynthesisResult` |
| STT | `STTProvider` | `async def transcribe(request: TranscriptionRequest) -> TranscriptionResult` |

---

## TTS Providerの追加

新しいTTSエンジンをProviderとして追加する。

### Step 1: Providerクラスを実装

`app/infrastructure/providers/<provider_name>/provider.py` を作成:

```python
from app.domain.value_objects.synthesis_request import ProviderSynthesisRequest
from app.domain.value_objects.synthesis_result import SynthesisResult


class QwenTTSProvider:
    provider_name: str = "qwen_tts"

    async def synthesize(
        self, request: ProviderSynthesisRequest
    ) -> SynthesisResult:
        # request.provider_config にProvider固有の設定が入っている
        # request.text に読み上げテキストが入っている
        # 実装...
        return SynthesisResult(audio_bytes=wav_bytes)
```

満たすべき制約:
- `provider_name` 属性を持つ
- `async def synthesize(self, request: ProviderSynthesisRequest) -> SynthesisResult` を実装する
- `SynthesisResult` は `audio_bytes: bytes`, `media_type: "audio/wav"`, `format: "wav"` で返す
- tmpファイルを使う場合は、bytes読み込み後に必ず削除する
- 同時実行数に制限を設ける場合は `asyncio.Semaphore` を使う

### Step 2: main.pyに登録

`app/main.py` のTTS Provider登録セクション（`if _mode in ("tts", "all"):` 内）に追加:

```python
from app.infrastructure.providers.qwen_tts.provider import QwenTTSProvider

if "qwen_tts" in configured_tts_providers:
    _tts_registry.register(QwenTTSProvider())
```

### Step 3: Model Profileを追加

`assets/models/models.yaml` に新しいmodelを追加（`direction: tts`）:

```yaml
models:
  # 既存のmodel...
  - id: qwen-default
    direction: tts
    object: model
    display_name: Qwen TTS Default
    provider: qwen_tts        # provider_nameと一致させる
    engine: base
    defaults:
      response_format: wav
      speed: 1.0
      timeout_sec: 120
    provider_config:
      model_name: Qwen/Qwen2.5-TTS
      device: cuda
```

### Step 4: Voice Profileにbindingを追加

各voiceの `profile.yaml` の `bindings` に新しいmodel用のエントリを追加:

```yaml
bindings:
  # 既存のbinding...
  qwen-default:
    provider_config:
      speaker: "female_01"
      seed: 42
```

### Step 5: テストを追加

1. `tests/infrastructure/qwen_tts/test_provider.py` — Provider単体テスト
2. 既存の統合テストで `qwen-default` + voiceの組み合わせを追加

---

## STT Providerの追加

新しいSTTエンジンをProviderとして追加する。

### Step 1: Providerクラスを実装

`app/infrastructure/providers/<provider_name>/provider.py` を作成:

```python
from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult


class WhisperProvider:
    provider_name: str = "whisper"

    async def transcribe(
        self, request: TranscriptionRequest
    ) -> TranscriptionResult:
        # request.audio_bytes に音声データが入っている
        # request.provider_config にProvider固有の設定が入っている
        # 実装...
        return TranscriptionResult(
            text="転写結果",
            language="ja",
            duration_sec=5.0,
            processing_ms=1200,
        )
```

満たすべき制約:
- `provider_name` 属性を持つ
- `async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult` を実装する
- `TranscriptionResult` の `duration_sec` と `processing_ms` は `>= 0`
- 音声バリデーションが必要な場合は専用のvalidatorモジュールを用意する

### Step 2: main.pyに登録

`app/main.py` のSTT Provider登録セクション（`if _mode in ("stt", "all"):` 内）に追加:

```python
from app.infrastructure.providers.whisper.provider import WhisperProvider

if "whisper" in configured_stt_providers:
    whisper_models = [m for m in stt_models if m.provider == "whisper"]
    whisper_model = whisper_models[0]
    _stt_registry.register(WhisperProvider(...))
```

### Step 3: Model Profileを追加

`assets/models/models.yaml` に新しいmodelを追加（`direction: stt`）:

```yaml
models:
  # 既存のmodel...
  - id: stt-whisper
    direction: stt
    object: model
    display_name: Whisper Large v3
    provider: whisper
    engine: large
    defaults:
      language: ja
      max_audio_seconds: 60
      timeout_sec: 120
    provider_config:
      model_id: openai/whisper-large-v3
```

### Step 4: テストを追加

1. `tests/infrastructure/whisper/test_provider.py` — Provider単体テスト
2. STT系のAPIテスト・統合テストに新しいmodelのケースを追加

---

## Voiceの追加

新しい声を追加する（TTSのみ）。以下では `your-voice-name` を例にしているため、実運用では任意のvoice IDに置き換える。

### Step 1: ディレクトリを作成

```bash
mkdir -p assets/voices/your-voice-name
```

### Step 2: profile.yamlを作成

テンプレートからコピー:

```bash
cp assets/voices/your-voice-name/profile.example.yaml assets/voices/your-voice-name/profile.yaml
```

内容を編集:

```yaml
voice_id: your-voice-name
display_name: your-voice-name
description: ここに声の説明を書く

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
      speaker_kv_scale: 1.0
```

### Step 3: 参照音声を配置

Irodoriのbase engineでは、`ref_wav_path`（WAV）または `ref_latent_path`（PT）のどちらかが必要。

```bash
# WAVで直接運用する場合
cp /path/to/your-voice-name_ref.wav assets/voices/your-voice-name/ref.wav

# PTがある場合はそちらが優先される
cp /path/to/your-voice-name_ref_latent.pt assets/voices/your-voice-name/ref_latent.pt
```

### Step 4: 動作確認

```bash
curl -X POST http://127.0.0.1:8012/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-default","voice":"your-voice-name","input":"テスト"}' \
  --output your-voice-name_test.wav
```

---

## Modelの追加

新しいmodelルートを追加する。同じProviderでもパラメータを変えて別ルートとして提供したい場合に使う。

### Step 1: models.yamlにエントリを追加

```yaml
models:
  # 既存...
  - id: irodori-high-quality
    direction: tts
    object: model
    display_name: Irodori High Quality
    provider: irodori
    engine: base
    defaults:
      response_format: wav
      speed: 1.0
      timeout_sec: 300    # 高品質なのでタイムアウトを長めに
    provider_config:
      checkpoint: Aratako/Irodori-TTS-500M-v2
      model_device: cuda
      codec_device: cuda
      model_precision: fp32
      codec_precision: fp32
```

### Step 2: 各voiceにbindingを追加（TTSの場合）

新しいmodel_idに対応するbindingを各voiceの `profile.yaml` に追加する。STT modelの場合はbinding不要。

### Step 3: 動作確認

```bash
curl http://127.0.0.1:8012/v1/models | jq '.data[] | select(.id=="irodori-high-quality")'
```

---

## 拡張チェックリスト

新規追加時の確認項目。

### TTS Provider追加

- [ ] `TTSProvider` Protocolを満たすクラスを実装した
- [ ] `provider_name` 属性を設定した
- [ ] `synthesize` が `SynthesisResult` を返す
- [ ] tmpファイルを使う場合、bytes読み込み後に削除する
- [ ] `main.py` のTTSセクションで `_tts_registry.register()` した
- [ ] 単体テストを書いた
- [ ] 既存テストが全て通る

### STT Provider追加

- [ ] `STTProvider` Protocolを満たすクラスを実装した
- [ ] `provider_name` 属性を設定した
- [ ] `transcribe` が `TranscriptionResult` を返す
- [ ] `duration_sec` と `processing_ms` が `>= 0` である
- [ ] 音声バリデーションを検討した
- [ ] `main.py` のSTTセクションで `_stt_registry.register()` した
- [ ] 単体テストを書いた
- [ ] 既存テストが全て通る

### Voice追加

- [ ] `assets/voices/<voice_id>/` ディレクトリを作成した
- [ ] `profile.yaml` の `voice_id` がディレクトリ名と一致する
- [ ] 利用する全modelのbindingを定義した
- [ ] 参照音声ファイル（.pt等）を配置した
- [ ] `GET /v1/voices` に表示される
- [ ] `POST /v1/audio/speech` で音声生成できる

### Model追加

- [ ] `models.yaml` にエントリを追加した
- [ ] `direction` を正しく設定した（`tts` / `stt`）
- [ ] `provider` が登録済みの `provider_name` と一致する
- [ ] TTS model: 全voiceにbindingを追加した（またはbindingなしで409を許容する）
- [ ] `GET /v1/models` に表示される
