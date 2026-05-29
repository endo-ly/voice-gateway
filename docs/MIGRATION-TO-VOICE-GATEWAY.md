# voice-gateway 統合計画

`stt-adapter` と `tts-adapter` を統合し、`voice-gateway` として再構成する計画。

## 目次

1. [背景と目的](#背景と目的)
2. [設計原則](#設計原則)
3. [前提条件と制約](#前提条件と制約)
4. [統合後のディレクトリ構成](#統合後のディレクトリ構成)
5. [ドメインモデルの拡張](#ドメインモデルの拡張)
6. [Application層の拡張](#application層の拡張)
7. [API設計](#api設計)
8. [設定・環境変数](#設定環境変数)
9. [Provider配置と依存関係](#provider配置と依存関係)
10. [マイグレーション手順](#マイグレーション手順)
11. [移行対象の現行コード対応表](#移行対象の現行コード対応表)
12. [リスクと緩和策](#リスクと緩和策)

---

## 背景と目的

### 現状

| | stt-adapter | tts-adapter |
|---|---|---|
| 役割 | 音声認識 (STT) | 音声合成 (TTS) |
| アーキテクチャ | Flat / プロトタイプ的 | Clean Architecture / 4層分離 |
| Provider抽象 | `ABC` 継承 | `Protocol` (構造型) |
| 設定管理 | YAML + 手作りパーサー | `pydantic-settings` + env vars |
| エラー設計 | `ProviderError` のみ | ドメインエラー階層 + `ErrorMapper` |
| プロファイル | なし | ModelProfile + VoiceProfile + VoiceBinding |
| テスト | 2ファイル | 層別 189本 |
| ドキュメント | READMEのみ | docs/ に6ファイル |

### 統合の理由

1. **保守コストの半減** — Provider抽象、エラー設計、設定管理、DIを二重に維持しなくてよい
2. **APIの一貫性** — クライアント（Bridge, OpenClaw等）が覚えることが半分になる
3. **プロファイルシステムの拡張** — ModelProfileに `direction` を追加するだけでSTTも同じ枠組みで管理できる
4. **共通インフラの再利用** — ErrorMapper, TempFileManager, Settings等がそのまま流用できる

### 統合後の名称

**`voice-gateway`**

---

## 設計原則

統合における最も重要な設計境界は、**何を共通化し、何を分けるか**である。

### 共通化するもの（外枠）

```text
HTTPエラー形式
設定読み込み (pydantic-settings)
ModelProfileRepository
起動mode制御
health / capabilities
tmp file管理
logging
テスト基盤
```

### 分けるもの（ドメイン動詞）

```text
TTSのvoice解決          ← STTはvoice概念を持たない
STTのaudio validation   ← TTSはaudio受信を持たない
TTS Provider Protocol   ← synthesize()
STT Provider Protocol   ← transcribe()
TTS Native API          ← /v1/speech
STT Native API          ← /v1/transcribe
```

**原則**: 共通化するのは外枠。分けるのはドメイン動詞。

TTSの動詞は `synthesize`。STTの動詞は `transcribe`。
これらを無理に `process_voice()` のように抽象化すると、設計が濁る。

---

## 前提条件と制約

### デプロイ形態

`voice-gateway` は、同一コードベースから以下の複数形態で起動できる。

| 形態 | 例 | 内容 |
|---|---|---|
| TTS only | Windows GPU機 | Irodori-TTS Providerのみを有効化 |
| STT only | ミニPC | ReazonSpeech K2 Providerのみを有効化 |
| STT + TTS | ミニPC / 開発環境 | 両Providerを有効化し、同一FastAPI appで両APIを提供 |

STT/TTSは必ず別環境で起動する必要はない。
同一マシン上で必要な依存関係が満たされていれば、`models.yaml` にSTT/TTS両方のmodelを定義することで、同一の `voice-gateway` インスタンスから両APIを提供できる。

有効化されるProviderは `VOICE_GATEWAY_MODE` と `models.yaml` に定義されたmodel/providerによって決まる。
そのため、使わないProviderはロードされず、対応する依存関係も必須ではない。

### 依存関係の性質の違い

| Provider | 呼び出し方式 | 配置 | 理由 |
|----------|------------|------|------|
| Irodori-TTS | subprocess (CLI) | 外部パス (`IRODORI_REPO_DIR`) | 上流がCLI前提。PyTorch等の依存が重く、adapter環境に混ぜたくない |
| ReazonSpeech K2 | Python import | `.vendor/` にclone → `pip install -e` | 上流がPythonパッケージとして設計されている |

この差は **Provider抽象が吸収する** ので、ドメイン層・API層には影響しない。

---

## 統合後のディレクトリ構成

```text
voice-gateway/
├── app/
│   ├── __init__.py
│   ├── main.py                              # FastAPI app (modeに応じたroutes登録)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py                  # FastAPI Depends (DI)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py                    # GET /health
│   │   │   ├── models.py                    # GET /v1/models
│   │   │   ├── voices.py                    # GET /v1/voices (mode=tts/all時のみ登録)
│   │   │   │
│   │   │   │  # ── TTS (mode=tts/all時のみ登録) ──
│   │   │   ├── openai_speech.py             # POST /v1/audio/speech
│   │   │   ├── native_speech.py             # POST /v1/speech
│   │   │   │
│   │   │   │  # ── STT (mode=stt/all時のみ登録) ──
│   │   │   ├── openai_transcriptions.py      # POST /v1/audio/transcriptions
│   │   │   ├── transcriptions.py            # POST /v1/transcribe
│   │   │   ├── transcriptions_latest.py     # GET /v1/transcriptions/latest
│   │   │   └── capabilities.py              # GET /v1/capabilities
│   │   │
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── error.py
│   │       ├── openai_speech.py
│   │       ├── native_speech.py
│   │       ├── transcription.py             # 新規: STTリクエスト/レスポンス
│   │       └── capabilities.py              # 新規: capabilitiesレスポンス
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── error_mapper.py              # 拡張: STTエラー追加
│   │   │   ├── model_resolver.py            # 新規: 共通 model検索 (direction考慮)
│   │   │   ├── tts_profile_resolver.py      # 既存ProfileResolverを改名
│   │   │   ├── stt_profile_resolver.py      # 新規: STT用 (voiceなし)
│   │   │   ├── tts_provider_registry.py     # TTS Provider専用Registry
│   │   │   ├── stt_provider_registry.py     # STT Provider専用Registry
│   │   │   └── option_merger.py             # TTS用 (STTは使用しない)
│   │   └── use_cases/
│   │       ├── __init__.py
│   │       ├── synthesize_speech.py         # TTS (既存)
│   │       ├── transcribe_audio.py          # STT (新規)
│   │       ├── get_latest_transcription.py  # STT (新規)
│   │       ├── list_models.py
│   │       └── list_voices.py
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── model_profile.py             # 拡張: direction フィールド + defaults型分離
│   │   │   └── voice_profile.py
│   │   ├── errors.py                        # 拡張: STT系エラー追加
│   │   ├── interfaces/
│   │   │   ├── __init__.py
│   │   │   ├── tts_provider.py              # 既存
│   │   │   ├── stt_provider.py              # 新規: STTProvider Protocol
│   │   │   ├── model_profile_repository.py
│   │   │   ├── voice_profile_repository.py
│   │   │   └── transcription_store.py       # 新規: TranscriptionStore Protocol
│   │   └── value_objects/
│   │       ├── __init__.py
│   │       ├── synthesis_request.py         # TTS → Provider
│   │       ├── synthesis_result.py          # TTS ← Provider
│   │       ├── transcription_request.py     # STT → Provider (新規)
│   │       └── transcription_result.py      # STT ← Provider (新規)
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py                  # 拡張: mode + STT用env vars
│   │   ├── logging/
│   │   │   ├── __init__.py
│   │   │   └── logger.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── fake/                        # 既存: テスト用TTSダミー
│   │   │   ├── irodori/                     # 既存: TTS Provider
│   │   │   └── reazonspeech_k2/             # 新規: STT Provider
│   │   │       ├── __init__.py
│   │   │       ├── provider.py              # ReazonSpeechK2Provider
│   │   │       └── audio_validator.py       # WAV検証 (stt_adapter/audio/validate.py から)
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── yaml_model_profile_repository.py
│   │   │   ├── yaml_voice_profile_repository.py
│   │   │   └── in_memory_transcription_store.py  # 新規: TranscriptionStoreのin-memory実装
│   │   ├── tempfiles/
│   │   │   ├── __init__.py
│   │   │   └── manager.py
│   │   └── events/
│   │       ├── __init__.py
│   │       └── stt_callback_dispatcher.py   # 新規: STT完了イベント専用
│   │
│   └── cli/
│       ├── __init__.py
│       ├── __main__.py
│       └── voices.py
│
├── assets/
│   ├── models/
│   │   ├── models.example.yaml              # テンプレート (STT + TTS 両方)
│   │   └── models.yaml                      # 実ファイル (gitignore)
│   └── voices/
│       └── <voice-id>/
│           ├── profile.example.yaml
│           └── profile.yaml
│
├── .vendor/                                 # .gitignore
│   └── reazonspeech-k2/                     # ミニPCのみ: clone & install
│
├── docs/
│   ├── architecture.md                      # 更新
│   ├── CONCEPT.md                           # 更新
│   ├── api-reference.md                     # 更新: STT endpoints追加
│   ├── configuration.md                     # 更新: STT設定追加
│   ├── development.md                       # 更新
│   ├── extension-guide.md                   # 更新: STT Provider追加手順
│   ├── providers/
│   │   ├── irodori.md                       # 既存
│   │   └── reazonspeech-k2.md              # 新規
│   └── MIGRATION-TO-VOICE-GATEWAY.md        # 本文档
│
├── scripts/
│   ├── install-reazonspeech-k2.sh           # stt-adapter から移行
│   ├── download-jsut-sample.sh              # stt-adapter から移行
│   ├── smoke-test-stt.sh                    # 新規 (stt-adapter の smoke-test.sh を改名)
│   └── irodori_encode_latent.py             # 既存
│
├── sample/                                  # .gitignore (STT動作確認用)
│
├── tests/
│   ├── conftest.py
│   ├── domain/
│   │   ├── test_errors.py                   # 拡張: STTエラー
│   │   ├── test_model_profile.py            # 拡張: directionバリデーション
│   │   ├── test_transcription_request.py    # 新規
│   │   ├── test_transcription_result.py     # 新規
│   │   └── ...
│   ├── infrastructure/
│   │   ├── reazonspeech_k2/                 # 新規
│   │   │   ├── test_provider.py
│   │   │   └── test_audio_validator.py
│   │   ├── test_stt_callback_dispatcher.py  # 新規
│   │   ├── test_in_memory_transcription_store.py  # 新規
│   │   └── ...
│   ├── application/
│   │   ├── test_model_resolver.py           # 新規
│   │   ├── test_stt_profile_resolver.py     # 新規
│   │   ├── test_transcribe_audio.py         # 新規
│   │   ├── test_get_latest_transcription.py # 新規
│   │   └── ...
│   ├── api/
│   │   ├── test_openai_transcriptions.py    # 新規
│   │   ├── test_transcriptions_route.py     # 新規
│   │   ├── test_capabilities.py             # 新規
│   │   └── ...
│   └── integration/
│       ├── test_acceptance.py               # 拡張: STT acceptance scenarios
│       └── test_stt_acceptance.py           # 新規
│
├── .env.example                             # 更新: mode + STT用env vars追加
├── pyproject.toml                           # 更新: name, optional deps
├── README.md                                # 全面更新
└── LICENSE
```

---

## ドメインモデルの拡張

### ModelProfile: `direction` フィールド + defaults型分離

```python
# app/domain/entities/model_profile.py

class TTSModelDefaults(BaseModel):
    """TTS用デフォルト値"""
    response_format: str = "wav"
    speed: float = 1.0
    timeout_sec: int = 120

class STTModelDefaults(BaseModel):
    """STT用デフォルト値"""
    language: str = "ja"
    max_audio_seconds: float = 30
    timeout_sec: int = 120

class ModelProfile(BaseModel):
    id: str
    object: str = "model"
    display_name: str
    direction: Literal["tts", "stt"] = "tts"    # 後方互換: デフォルトtts
    provider: str
    engine: str
    defaults: TTSModelDefaults | STTModelDefaults = Field(default_factory=TTSModelDefaults)
    provider_config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_defaults(self) -> "ModelProfile":
        """directionに応じてdefaultsの型を確定させる。
        
        PydanticのUnionは定義順やextra fieldの扱いによって意図しない型に
        寄る可能性があるため、model_validatorでdirection連動のvalidationを
        必ず行う。direction=sttのときはSTTModelDefaults、
        direction=ttsのときはTTSModelDefaultsとして解釈されることを保証する。
        """
        if isinstance(self.defaults, dict):
            self.defaults = (
                STTModelDefaults(**self.defaults)
                if self.direction == "stt"
                else TTSModelDefaults(**self.defaults)
            )
        return self
```

models.yamlでの表現:

```yaml
models:
  # TTS
  - id: tts-default
    direction: tts
    provider: irodori
    engine: base
    display_name: Default TTS
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
    provider: reazonspeech_k2
    engine: k2
    display_name: ReazonSpeech K2 v2
    defaults:
      language: ja
      max_audio_seconds: 30
      timeout_sec: 120
    provider_config:
      model_id: reazon-research/reazonspeech-k2-v2
      precision: fp32
```

### 新規: STTProvider Protocol

TTSの `TTSProvider` とは完全に独立したProtocol。

```python
# app/domain/interfaces/stt_provider.py

from typing import Protocol, runtime_checkable
from app.domain.value_objects.transcription_request import TranscriptionRequest
from app.domain.value_objects.transcription_result import TranscriptionResult

@runtime_checkable
class STTProvider(Protocol):
    provider_name: str

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult: ...

    def is_loaded(self) -> bool: ...

    def capabilities(self) -> dict: ...
```

### 新規: STT Value Objects

```python
# app/domain/value_objects/transcription_request.py

class TranscriptionRequest(BaseModel):
    model_id: str
    audio_path: str                    # 一時ファイルパス
    language: str = "ja"
    provider: str
    engine: str
    provider_config: dict[str, Any]

# app/domain/value_objects/transcription_result.py

class TranscriptionResult(BaseModel):
    text: str
    language: str
    duration_sec: float
    processing_ms: int
    provider: str
    model: str
    audio_info: dict | None = None     # sampleRate, channels, format
```

### 新規: TranscriptionStore Interface

```python
# app/domain/interfaces/transcription_store.py

from typing import Protocol
from app.domain.value_objects.transcription_result import TranscriptionResult

class TranscriptionStore(Protocol):
    def set_latest(self, result: TranscriptionResult, source: str) -> None: ...
    def get_latest(self) -> TranscriptionResult | None: ...
```

### エラー階層の拡張

現行の `TTSAdapterError` を `VoiceGatewayError` にリネームし、STT系エラーを追加:

```python
# app/domain/errors.py

class VoiceGatewayError(Exception):
    """Base error for all voice-gateway domain errors."""

# ── 共通 ──
class ModelNotFoundError(VoiceGatewayError): ...
class ProviderNotFoundError(VoiceGatewayError): ...
class ProviderExecutionError(VoiceGatewayError): ...
class ProviderTimeoutError(VoiceGatewayError): ...
class InvalidProfileError(VoiceGatewayError): ...

# ── TTS ──
class VoiceNotFoundError(VoiceGatewayError): ...
class VoiceBindingNotFoundError(VoiceGatewayError): ...
class UnsupportedResponseFormatError(VoiceGatewayError): ...
class UnsupportedSpeedError(VoiceGatewayError): ...
class InvalidProviderConfigError(VoiceGatewayError): ...

# ── STT (新規) ──
class AudioValidationError(VoiceGatewayError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)

class AudioTooLargeError(VoiceGatewayError): ...
class AudioTooLongError(VoiceGatewayError): ...
class TranscriptionFailedError(VoiceGatewayError): ...
class ModelNotLoadedError(VoiceGatewayError): ...
```

ErrorMapperの拡張:

```python
# error_mapper.py の mapping に追加
AudioValidationError:    (400, "audio_validation_error", "file"),
AudioTooLargeError:      (400, "audio_too_large", "file"),
AudioTooLongError:       (400, "audio_too_long", "file"),
TranscriptionFailedError: (500, "transcription_failed", None),
ModelNotLoadedError:     (503, "model_not_loaded", None),
```

---

## Application層の拡張

### ModelResolver (共通)

model_idとdirectionの検証を担当。TTS/STT双方のResolverが依存する。

```python
# app/application/services/model_resolver.py

class ModelResolver:
    def __init__(self, model_repo: ModelProfileRepository) -> None:
        self._model_repo = model_repo

    def get_model(self, model_id: str, direction: str | None = None) -> ModelProfile:
        model = self._model_repo.get_by_id(model_id)
        if direction is not None and model.direction != direction:
            raise ModelNotFoundError(model_id)
        return model
```

### TTSProfileResolver (既存を改名)

voice解決、VoiceBinding確認、5層option mergeを行う。TTS専用。

```python
# app/application/services/tts_profile_resolver.py

class TTSProfileResolver:
    def __init__(
        self,
        model_resolver: ModelResolver,
        voice_repo: VoiceProfileRepository,
        option_merger: OptionMerger,
    ) -> None: ...

    def resolve(self, model_id: str, voice_id: str, request_options: dict | None = None) -> tuple[ModelProfile, VoiceProfile, dict]:
        model = self._model_resolver.get_model(model_id, direction="tts")
        voice = self._voice_repo.get_by_id(voice_id)
        binding = voice.bindings.get(model_id)
        if binding is None:
            raise VoiceBindingNotFoundError(voice_id, model_id)
        merged = self._merger.merge(...)
        return model, voice, merged
```

### STTProfileResolver (新規)

voice解決なし。modelのprovider_configとrequest_optionsのマージのみ。STT専用。

設定の優先順位（後勝ち）:

```text
STT設定の優先順位:
1. request_options   (最優先: APIリクエストからの指定)
2. model.provider_config  (Provider固有設定)
3. model.defaults    (モデル既定値)
```

`max_audio_seconds` はProvider制約として `provider_config` 側に置くことも可能だが、
API上の共通制約として扱うなら `defaults` 側でも問題ない。

```python
# app/application/services/stt_profile_resolver.py

class STTProfileResolver:
    def __init__(self, model_resolver: ModelResolver) -> None:
        self._model_resolver = model_resolver

    def resolve(self, model_id: str, request_options: dict | None = None) -> tuple[ModelProfile, dict]:
        model = self._model_resolver.get_model(model_id, direction="stt")
        config: dict = {}
        config.update(model.defaults.model_dump())
        config.update(model.provider_config)
        if request_options:
            config.update(request_options)
        return model, config
```

### Provider Registryの分離

`synthesize()` と `transcribe()` は互換ではないため、RegistryをTTS/STTで分ける。

```python
# app/application/services/tts_provider_registry.py

class TTSProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, TTSProvider] = {}

    def register(self, provider: TTSProvider) -> None:
        self._providers[provider.provider_name] = provider

    def get(self, name: str) -> TTSProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderNotFoundError(name)
        return provider

# app/application/services/stt_provider_registry.py

class STTProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, STTProvider] = {}

    def register(self, provider: STTProvider) -> None:
        self._providers[provider.provider_name] = provider

    def get(self, name: str) -> STTProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderNotFoundError(name)
        return provider
```

---

## API設計

### エンドポイント一覧

Routesは `VOICE_GATEWAY_MODE` に応じて登録される:

| mode | 登録されるroutes |
|------|---------------|
| 共通 | health, models, capabilities |
| `tts` | voices, openai_speech, native_speech |
| `stt` | openai_transcriptions, transcriptions, transcriptions_latest |
| `all` | 全routes |

#### 共通

| Method | Path | 説明 |
|--------|------|------|
| GET | `/health` | ヘルスチェック (mode + providers状態を含む) |
| GET | `/v1/models` | model一覧 (`direction` フィルタ + レスポンスに`direction`フィールド含む) |
| GET | `/v1/capabilities` | 機能判定 (tts/stt enabled/providers) |

#### TTS (mode=tts/all)

| Method | Path | 説明 |
|--------|------|------|
| GET | `/v1/voices` | voice一覧 |
| POST | `/v1/audio/speech` | OpenAI互換 TTS |
| POST | `/v1/speech` | ネイティブ TTS (拡張パラメータ) |

mode=stt時はTTS routesを登録しないため、`/v1/voices` も存在しない。
クライアントは `/v1/capabilities` の `tts.enabled` を確認してから利用する。

#### STT (mode=stt/all)

| Method | Path | 説明 |
|--------|------|------|
| POST | `/v1/audio/transcriptions` | OpenAI互換 STT |
| POST | `/v1/transcribe` | ネイティブ STT |
| GET | `/v1/transcriptions/latest` | 直近の文字起こし結果 |
| GET | `/v1/capabilities` | voice-gateway capabilities |

### OpenAI互換STT: 入力仕様

OpenAIのtranscription APIに寄せる。`source`はNative専用。

```python
@router.post("/v1/audio/transcriptions")
async def openai_transcriptions(
    file: UploadFile = File(...),
    model: str = Form("stt-default"),
    language: str | None = Form(None),
    response_format: str = Form("json"),
    prompt: str | None = Form(None),
):
    ...
```

OpenAI互換側は薄く保ち、詳細情報（`processingMs`, `audio`等）はNative側に寄せる。

```text
/v1/audio/transcriptions  # OpenAI互換: file, model, language, response_format, prompt
/v1/transcribe            # Native: file, model, source, emit_event, callback
```

### レスポンス形式

**TTS** (既存、変更なし):
```json
// 成功: audio/wav binary
// エラー: { "error": { "message", "type", "param", "code" } }
```

**STT OpenAI互換** (薄く):
```json
{
  "text": "だが、エーアイセンター稼動を..."
}
```

**STT ネイティブ** (詳細):
```json
{
  "ok": true,
  "data": {
    "text": "...",
    "language": "ja",
    "durationSec": 5.234,
    "processingMs": 1200,
    "provider": "reazonspeech_k2",
    "model": "reazon-research/reazonspeech-k2-v2",
    "audio": { "sampleRate": 16000, "channels": 1, "format": "wav" },
    "source": "stackchan"
  }
}
```

**エラー** (TTS/STT共通形式):
```json
{
  "error": {
    "message": "Audio duration exceeds 30 seconds",
    "type": "invalid_request_error",
    "param": "file",
    "code": "audio_too_long"
  }
}
```

### GET /v1/models の拡張

`direction` クエリパラメータでフィルタ。レスポンスにも `direction` フィールドを含める。

```bash
# 全model
curl http://localhost:8012/v1/models

# TTSのみ
curl http://localhost:8012/v1/models?direction=tts

# STTのみ
curl http://localhost:8012/v1/models?direction=stt
```

### GET /v1/voices の扱い

mode=stt時はvoices routeを登録しない。クライアントは `/v1/capabilities` でtts.enabledを確認してからvoicesにアクセスすべき。

### /health の拡張

modeとProvider状態を表示。modeに応じて有効なProviderのみを表示するのではなく、
TTS/STT双方のProvider状態を含めて `/v1/capabilities` との見え方を統一する。

```json
{
  "status": "ok",
  "mode": "stt",
  "providers": {
    "tts": {
      "enabled": false,
      "providers": []
    },
    "stt": {
      "enabled": true,
      "providers": {
        "reazonspeech_k2": { "loaded": true }
      }
    }
  }
}
```

### GET /v1/capabilities

クライアントがどの機能を使えるかを判定する:

```json
{
  "tts": {
    "enabled": true,
    "providers": ["irodori"]
  },
  "stt": {
    "enabled": true,
    "providers": ["reazonspeech_k2"]
  }
}
```

---

## 設定・環境変数

### 環境変数 (pydantic-settings)

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `VOICE_GATEWAY_MODE` | No | `all` | 起動mode: `tts`, `stt`, `all`。有効なroutesとProviderを制御する。開発用途では `all` が便利だが、常駐運用では `tts` / `stt` / `all` を明示することを推奨する |
| `HOST` | No | `127.0.0.1` | 待受ホスト |
| `PORT` | No | `8012` | 待受ポート |
| `LOG_LEVEL` | No | `INFO` | ログレベル |
| `ASSETS_DIR` | No | `assets` | プロファイル配置ディレクトリ |
| `TMP_DIR` | No | `tmp` | 一時ファイル出力ディレクトリ |
| `TIMEOUT_SEC` | No | `120` | Provider実行タイムアウト |
| `MAX_CONCURRENCY` | No | `1` | 同時実行数上限 |
| `PROJECT_ROOT` | No | リポジトリルート | 相対パス解決基準 |
| | | | |
| **TTS** | | | |
| `IRODORI_REPO_DIR` | TTS利用時 | なし | Irodori-TTSリポジトリパス |
| | | | |
| **STT** | | | |
| `REAZONSPEECH_REPO_DIR` | No | `.vendor/ReazonSpeech` | ReazonSpeech リポジトリのclone先ルートパス |
| `STT_CALLBACK_URL` | No | なし | STT完了コールバック先URL (例: `http://127.0.0.1:8787/stt/events`) |
| `STT_CALLBACK_TIMEOUT_MS` | No | `3000` | コールバックタイムアウト |

### VOICE_GATEWAY_MODE の挙動

`VOICE_GATEWAY_MODE` は起動時にどのAPI群を有効化するかを決定する。
`models.yaml` はそのAPI群で使うmodel/provider定義を与える。

| mode | 登録routes | ロードproviders |
|------|-----------|---------------|
| `tts` | TTS routes only | direction=tts の models の provider |
| `stt` | STT routes only | direction=stt の models の provider |
| `all` | TTS + STT routes | 両方 |

modeとmodels.yamlの組み合わせによる事故防止:

```text
VOICE_GATEWAY_MODE=tts なのに models.yaml に stt model が書いてある
  → mode=tts なので STT routes は登録されない
  → STT providers もロードされない
  → ReazonSpeech import は試みられない（事故回避）
```

### 設定の統合アプローチ

stt-adapterの `config.yaml` 方式は廃止し、全て **pydantic-settings + env vars + YAMLプロファイル** に統一する。

- Provider固有設定 (precision, language, max_audio_seconds等) → `models.yaml` の `provider_config` に移行
- Audio設定 (sample_rate, channels等) → `models.yaml` の `provider_config` に移行
- Events/Callback設定 → 環境変数に移行

---

## Provider配置と依存関係

### pyproject.toml

```toml
[project]
name = "voice-gateway"
version = "0.1.0"
description = "Unified voice gateway for STT and TTS"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.136.1",
    "uvicorn[standard]>=0.46.0",
    "pydantic>=2.13.3",
    "pyyaml>=6.0.3",
    "pydantic-settings>=2.14.0",
    "python-multipart>=0.0.20",        # STT: UploadFile用
]

[project.optional-dependencies]
reazonspeech-k2 = [
    "sherpa-onnx>=1.10.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "httpx>=0.28.1",
]
```

### インストールパターン

```bash
# Windows GPU機 (TTS only)
uv sync --group dev
# Irodoriはsubprocessなのでextras不要

# ミニPC (STT only)
uv sync --group dev --extra reazonspeech-k2
# ReazonSpeechはPython importなのでextras必要

# ミニPC / 開発環境 (STT + TTS)
uv sync --group dev --extra reazonspeech-k2
# Irodoriを同じマシンで使う場合は IRODORI_REPO_DIR も設定する
```

### .vendor/ の扱い

```text
voice-gateway/
├── .vendor/                             # .gitignore
│   └── reazonspeech-k2/                 # ミニPCのみ
│       └── ReazonSpeech/                # git clone
│           └── pkg/k2-asr/              # pip install -e 対象
│
├── scripts/
│   └── install-reazonspeech-k2.sh       # clone + install を自動化
```

Irodoriは `.vendor/` に置かない。`IRODORI_REPO_DIR` で外部パスを指す（現状通り）。

### main.py での起動・Provider登録 (拡張後)

```python
# app/main.py

app = FastAPI(title="voice-gateway", version="0.1.0")

_settings = Settings()
setup_logging(_settings.log_level)

_model_repo = YamlModelProfileRepository(...)
_voice_repo = YamlVoiceProfileRepository(...)

# ── 共通 ──
app.include_router(health_router)
app.include_router(models_router)

_mode = _settings.mode  # "tts" | "stt" | "all"

# ── TTS Providers & Routes ──
_tts_registry = TTSProviderRegistry()
if _mode in ("tts", "all"):
    tts_models = [m for m in _model_repo.list_all() if m.direction == "tts"]
    configured_tts_providers = {m.provider for m in tts_models}

    if "fake" in configured_tts_providers:
        _tts_registry.register(FakeProvider())
    if "irodori" in configured_tts_providers:
        _tts_registry.register(IrodoriProvider(...))

    _model_resolver = ModelResolver(_model_repo)
    _tts_resolver = TTSProfileResolver(_model_resolver, _voice_repo, OptionMerger())

    app.include_router(voices_router)
    app.include_router(openai_speech_router)
    app.include_router(native_speech_router)

    app.state.synthesize_speech = SynthesizeSpeech(
        profile_resolver=_tts_resolver,
        provider_registry=_tts_registry,
    )

# ── STT Providers & Routes ──
_stt_registry = STTProviderRegistry()
if _mode in ("stt", "all"):
    stt_models = [m for m in _model_repo.list_all() if m.direction == "stt"]
    configured_stt_providers = {m.provider for m in stt_models}

    if "reazonspeech_k2" in configured_stt_providers:
        _stt_registry.register(ReazonSpeechK2Provider(...))

    _model_resolver = ModelResolver(_model_repo) if _mode == "stt" else _model_resolver
    _stt_resolver = STTProfileResolver(_model_resolver)
    _transcription_store = InMemoryTranscriptionStore()

    app.include_router(capabilities_router)
    app.include_router(openai_transcriptions_router)
    app.include_router(transcriptions_router)
    app.include_router(transcriptions_latest_router)

    app.state.transcribe_audio = TranscribeAudio(
        profile_resolver=_stt_resolver,
        provider_registry=_stt_registry,
        transcription_store=_transcription_store,
    )
    app.state.get_latest_transcription = GetLatestTranscription(
        transcription_store=_transcription_store,
    )
```

---

## マイグレーション手順

### Phase 0: voice-gateway化の余地を作る (tts-adapter内で実施)

リネーム前に設計の受け皿を作る。差分を最小限にする。

1. `ProviderRegistry` → `TTSProviderRegistry` にリネーム
2. `ProfileResolver` → `TTSProfileResolver` にリネーム
3. `ModelProfile` に `direction: Literal["tts", "stt"] = "tts"` を追加（後方互換）
4. `ModelDefaults` → `TTSModelDefaults` にリネーム
5. `VOICE_GATEWAY_MODE` 設定を `Settings` に追加（現状は `all` のみ使用）
6. 既存TTSテストが全て通ることを確認

### Phase 1: リネーム (voice-gateway化)

1. tts-adapter を voice-gateway にリネーム (repo rename)
2. `pyproject.toml` の `name` を `voice-gateway` に変更
3. `TTSAdapterError` → `VoiceGatewayError` にリネーム (全ファイル)
4. 全ドキュメントの "tts-adapter" 表記を "voice-gateway" に更新
5. 既存テストが全て通ることを確認

### Phase 2: ドメイン層の拡張

1. `STTModelDefaults` を追加
2. `ModelProfile.defaults` の型を `TTSModelDefaults | STTModelDefaults` に変更
3. `STTProvider` Protocol を追加
4. `TranscriptionRequest` / `TranscriptionResult` Value Object を追加
5. `TranscriptionStore` Protocol を追加
6. STT系エラークラスを追加
7. `ErrorMapper` にSTTエラーマッピングを追加
8. テストを追加 (Domain層)

### Phase 3: Application層の拡張

1. `ModelResolver` を追加 (共通model検索)
2. `STTProfileResolver` を追加 (voiceなし)
3. `STTProviderRegistry` を追加
4. `TranscribeAudio` ユースケースを追加
5. `GetLatestTranscription` ユースケースを追加
6. テストを追加 (Application層)

### Phase 4: Infrastructure層の拡張

1. `ReazonSpeechK2Provider` を `app/infrastructure/providers/reazonspeech_k2/` に実装
2. `audio_validator.py` を `stt_adapter/audio/validate.py` から移行
3. `InMemoryTranscriptionStore` を実装
4. `SttCallbackDispatcher` を `stt_adapter/events.py` から移行
5. `Settings` にSTT用環境変数を追加
6. テストを追加 (Infrastructure層)

### Phase 5: API層の拡張

1. STT routes を追加 (`openai_transcriptions.py`, `transcriptions.py`, `transcriptions_latest.py`, `capabilities.py`)
2. STT schemas を追加
3. `main.py` のmode分岐ロジックでSTT routesとDIを登録
4. `/health` を拡張 (mode + providers)
5. `/v1/models` に `direction` フィルタとレスポンスフィールドを追加
6. テストを追加 (API層)

### Phase 6: 統合と仕上げ

1. 統合テストにSTT acceptance scenarioを追加
2. `models.example.yaml` にSTT modelテンプレートを追加
3. ドキュメント更新 (全ファイル)
4. scripts/ にSTT関連スクリプトを追加
5. stt-adapter repoを archive にする

---

## 移行対象の現行コード対応表

### stt-adapter → voice-gateway 移行マッピング

| stt-adapter | voice-gateway | 備考 |
|-------------|---------------|------|
| `stt_adapter/api/routes.py` | `app/api/routes/openai_transcriptions.py` + `transcriptions.py` + `transcriptions_latest.py` | 1ファイル→3ファイルに分割（tts-adapterのroute分割パターンに合わせる） |
| `stt_adapter/api/schemas.py` | `app/api/schemas/transcription.py` + `app/domain/value_objects/transcription_result.py` | API schemaとdomain value objectに分離 |
| `stt_adapter/providers/base.py` (`SttProvider` ABC) | `app/domain/interfaces/stt_provider.py` (Protocol) | ABC → Protocol に変更（tts-adapterの設計に統一） |
| `stt_adapter/providers/base.py` (`ProviderError`) | `app/domain/errors.py` (各エラークラス) | 単一ProviderError → エラー階層に分解 |
| `stt_adapter/providers/reazonspeech_k2/provider.py` | `app/infrastructure/providers/reazonspeech_k2/provider.py` | そのまま移行、Protocol適合に修正 |
| `stt_adapter/audio/validate.py` | `app/infrastructure/providers/reazonspeech_k2/audio_validator.py` | Provider配下に配置 |
| `stt_adapter/audio/types.py` (`AudioInfo`) | Provider内に配置 | ReazonSpeech専用のためProvider内で定義 |
| `stt_adapter/audio/convert.py` | 削除 | `NotImplementedError` のみ。必要になった時に実装 |
| `stt_adapter/config/types.py` | `app/infrastructure/config/settings.py` + `models.yaml` | dataclass → pydantic-settings + YAMLプロファイル |
| `stt_adapter/config/load_config.py` | 削除 | pydantic-settings が代替 |
| `stt_adapter/events.py` (`TranscriptionStore`) | `app/infrastructure/repositories/in_memory_transcription_store.py` | 「latest transcriptionを保持する保存先」なのでrepositories配下。Protocol → InMemory実装のClean Architecture対応 |
| `stt_adapter/events.py` (`dispatch_callbacks`) | `app/infrastructure/events/stt_callback_dispatcher.py` | STT完了イベント専用。TTSイベントは将来一般化時に対応 |
| `stt_adapter/__init__.py` (`__version__`) | `app/__init__.py` に統合 | |
| `apps/stt_adapter_api/main.py` | 削除 | `app/main.py` に統合 |
| `config.example.yaml` | `assets/models/models.example.yaml` に統合 | YAMLプロファイル方式に移行 |
| `scripts/*` | `scripts/*` に移行 | |
| `sample/*` | `sample/*` に移行 | |
| `tests/test_api_routes.py` | `tests/api/test_openai_transcriptions.py` 等 | 層別テストパターンに再構成 |
| `tests/test_audio_validate.py` | `tests/infrastructure/reazonspeech_k2/test_audio_validator.py` | |

---

## リスクと緩和策

### リスク1: ReazonSpeech K2 の Python import 方式が async 対応していない

**現状**: `ReazonSpeechK2Provider.transcribe_file()` は同期メソッド。

**緩和策**: `asyncio.to_thread()` でラップして非同期化する。STTProvider Protocol を `async def transcribe()` にしているのはこのため。

```python
async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
    return await asyncio.to_thread(self._transcribe_sync, request)
```

### リスク2: stt-adapter の `/transcribe` レスポンス形式が TTS と異なる

**現状**: stt-adapterは `{"ok": true, "data": {...}}` ラッパーを使うが、tts-adapterは使わない。

**緩和策**:
- `/v1/audio/transcriptions` (OpenAI互換) → ラッパーなし（OpenAI仕様に合わせる、薄く保つ）
- `/v1/transcribe` (ネイティブ) → `{"ok": true, "data": {...}}` ラッパーあり（現行stt-adapterの形式を維持）

この二重アプローチはTTS側が既に採用しているパターン（OpenAI互換 + ネイティブの2系統）と一致する。

### リスク3: デプロイ環境が分かれることで使わないコードが残る

**現状**: Windows機ではSTTコードが、ミニPCではTTSコードがデッドコードになる。

**緩和策**: `VOICE_GATEWAY_MODE` でroutesとProvider登録を制御するため、使わないProviderのimportも発生しない。optional extrasで依存も分離済み。

### リスク4: ModelProfile.direction が既存のTTSモデルに影響する

**現状**: 既存の `models.yaml` に `direction` フィールドがない。

**緩和策**: `direction` のデフォルト値を `"tts"` にする。既存のmodels.yamlはそのまま動く。

```python
class ModelProfile(BaseModel):
    direction: Literal["tts", "stt"] = "tts"   # 既存レコードへの後方互換
```

### リスク5: 共通化しすぎてSTT/TTSのドメイン境界が曖昧になる

**緩和策**: 設計原則「共通化するのは外枠、分けるのはドメイン動詞」を厳守する。

```text
共通化: HTTPエラー形式、設定読み込み、ModelProfileRepository、起動mode制御、
        health/capabilities、tmp管理、logging、テスト基盤

分離:   TTSのvoice解決、STTのaudio validation、
        TTS Provider Protocol / STT Provider Protocol、
        TTS Native API / STT Native API
```

TTSの動詞は `synthesize`、STTの動詞は `transcribe`。これらを無理に統一した抽象 (`process_voice()`等) は作らない。
