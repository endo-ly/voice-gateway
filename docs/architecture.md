# アーキテクチャ

voice-gatewayの内部構造を説明する。

## 設計原則

1. **voiceはProviderに固定しない** — `voice_id` は論理的な声のIDであり、特定のTTSエンジンに紐付かない
2. **Provider / engineはModelProfileが正** — VoiceProfile側にProvider情報を重複して持たせない
3. **層をまたぐ依存は下向きのみ** — API→Application→Domain←Infrastructure。逆方向の依存はない
4. **共通化するのは外枠、分けるのはドメイン動詞** — Registry・Resolverは方向ごとに分割し、共通部分（ModelResolver・OptionMerger）は共有する

## レイヤー構成

```
┌─────────────────────────────────┐
│  API層 (app/api/)               │  HTTP入出力、status code
│  routes / schemas               │
├─────────────────────────────────┤
│  Application層 (app/application/)│  ユースケース、プロファイル解決、設定マージ
│  use_cases / services           │
├─────────────────────────────────┤
│  Domain層 (app/domain/)         │  中核概念、interface、domain error
│  entities / value_objects /     │
│  interfaces / errors            │
├─────────────────────────────────┤
│  Infrastructure層               │  YAML読み込み、Provider実装、subprocess、コールバック
│  (app/infrastructure/)          │
│  config / repositories /        │
│  providers / events / tempfiles │
└─────────────────────────────────┘
```

各層の責務:

| 層 | 責務 | 依存方向 |
|---|------|---------|
| API | HTTPリクエスト/レスポンス、schema validation、status code決定 | → Application |
| Application | model/voice解決、Provider選択、設定マージ、ユースケース実行 | → Domain |
| Domain | 中核概念（ModelProfile, VoiceProfile, 各種Request/Result等）、Protocol定義、domain error | 依存なし |
| Infrastructure | YAML読み込み、Provider実装、subprocess実行、tmp管理、コールバック送信 | → Domain（interfaceを実装） |

API層にProvider選択ロジックを書かない。Infrastructure層にHTTPリクエストの都合を書かない。

## データフロー

### TTS（音声合成）

```
client
  │ model=tts-default, voice=your-voice-name
  ▼
API層 (routes/openai_speech.py)
  │ requestをschemaでvalidation
  ▼
Application層 (use_cases/synthesize_speech.py)
  │
  ├─ TTSProfileResolver.resolve(model_id, voice_id)
  │   ├─ ModelResolver → ModelProfile
  │   ├─ VoiceProfileRepository → VoiceProfile
  │   ├─ VoiceBinding の存在確認
  │   └─ OptionMerger.merge(5層の設定) → merged config
  │
  ├─ TTSProviderRegistry.get(provider_name) → TTSProvider
  │
  └─ provider.synthesize(ProviderSynthesisRequest) → SynthesisResult
      │
      ▼
Infrastructure層 (IrodoriProvider 等)
  │ CLI command組み立て → subprocess実行 → tmp wav読み込み → bytes返却
  ▼
API層
  │ Response(content=audio_bytes, media_type=audio/wav)
  ▼
client
```

### STT（音声認識）

```
client
  │ file=audio.wav, model=stt-default
  ▼
API層 (routes/openai_transcriptions.py)
  │ file upload + schema validation
  ▼
Application層 (use_cases/transcribe_audio.py)
  │
  ├─ STTProfileResolver.resolve(model_id)
  │   ├─ ModelResolver → ModelProfile (direction=stt)
  │   └─ provider_config の取得
  │
  ├─ STTProviderRegistry.get(provider_name) → STTProvider
  │
  └─ provider.transcribe(TranscriptionRequest) → TranscriptionResult
      │
      ▼
Infrastructure層 (ReazonSpeechK2Provider)
  │ audio_validator で検証 → model推論 → asyncio.to_thread() で同期ラップ
  ▼
Application層
  │ TranscriptionStore に結果を保存
  │ SttCallbackDispatcher でコールバック送信 (非同期)
  ▼
API層
  │ Response: OpenAI互換 or Native 形式
  ▼
client
```

## サービスの分割

TTSとSTTで共通する部分と方向固有の部分を明確に分けている。

### 共通サービス

| クラス | 役割 |
|--------|------|
| `ModelResolver` | model_id → ModelProfile の解決（directionの検証含む） |
| `OptionMerger` | 5層の設定を優先度順にマージ |
| `ErrorMapper` | domain error → HTTP status + OpenAI互換error body |

### 方向固有サービス

| クラス | 方向 | 役割 |
|--------|------|------|
| `TTSProfileResolver` | TTS | model + voiceの解決、binding存在確認、設定マージ |
| `TTSProviderRegistry` | TTS | provider_name → TTSProviderのlookup |
| `STTProfileResolver` | STT | modelの解決、provider_configの取得 |
| `STTProviderRegistry` | STT | provider_name → STTProviderのlookup |

## 主要クラス

### Domain

| クラス | 役割 |
|--------|------|
| `ModelProfile` | model定義（id, direction, provider, engine, defaults, provider_config） |
| `VoiceProfile` | voice定義（voice_id, display_name, bindings） |
| `VoiceBinding` | model_idごとのprovider_config |
| `TTSModelDefaults` | TTS向けデフォルト値（response_format, speed, timeout_sec） |
| `STTModelDefaults` | STT向けデフォルト値（language, max_audio_seconds, timeout_sec） |
| `ProviderSynthesisRequest` | TTS Providerへの入力（text, config, format等） |
| `SynthesisResult` | TTS Providerからの出力（audio_bytes, media_type） |
| `TranscriptionRequest` | STT Providerへの入力（audio_bytes, config等） |
| `TranscriptionResult` | STT Providerからの出力（text, language, duration_sec, processing_ms） |
| `VoiceGatewayError` | 全domain errorの基底クラス |

### Application

| クラス | 役割 |
|--------|------|
| `SynthesizeSpeech` | TTS ユースケース（validation → resolve → dispatch） |
| `TranscribeAudio` | STT ユースケース（resolve → transcribe → store → callback） |
| `GetLatestTranscription` | 直近の転写結果取得ユースケース |
| `ListModels` | model一覧取得 |
| `ListVoices` | voice一覧取得 |

### Infrastructure

| クラス | 役割 |
|--------|------|
| `YamlModelProfileRepository` | models.yamlの読み込み（safe_load + Pydantic validation、キャッシュ付き） |
| `YamlVoiceProfileRepository` | voices/*/profile.yamlの読み込み |
| `InMemoryTranscriptionStore` | 転写結果のインメモリ保持・最新1件の取得 |
| `IrodoriProvider` | Irodori CLI subprocess実行（Semaphore=1、tmp管理） |
| `IrodoriCliBuilder` | engine種別に応じたCLI引数のlist[str]組み立て |
| `SubprocessRunner` | asyncio.create_subprocess_execのラッパー（timeout、exit code、stderr捕捉） |
| `ReazonSpeechK2Provider` | ReazonSpeech K2によるSTT推論（マルチモデルキャッシュ付き） |
| `SttCallbackDispatcher` | 転写結果の非同期コールバック送信 |
| `TempFileManager` | uuid付きtmp wavパスの発行と削除 |
| `FakeProvider` | テスト・開発用のダミーTTS Provider（最小有効WAVを返す） |

## エラー設計

domain errorは `VoiceGatewayError` を継承し、Application層の `ErrorMapper` がHTTPステータスに変換する。

### TTS系

```
VoiceGatewayError
├── ModelNotFoundError              → 404
├── VoiceNotFoundError              → 404
├── VoiceBindingNotFoundError       → 409
├── UnsupportedResponseFormatError  → 400
├── UnsupportedSpeedError           → 400
├── ProviderNotFoundError           → 500
├── ProviderExecutionError          → 500
├── ProviderTimeoutError            → 504
├── InvalidProfileError             → 500
└── InvalidProviderConfigError      → 400
```

### STT系

```
VoiceGatewayError
├── ModelNotFoundError              → 404
├── ProviderNotFoundError           → 500
├── TranscriptionFailedError        → 500
├── ModelNotLoadedError             → 503
├── AudioValidationError            → 400
├── AudioTooLargeError              → 400
├── AudioTooLongError               → 400
├── InvalidProviderConfigError      → 400
└── ProviderTimeoutError            → 504
```

エラー形式はOpenAI互換:

```json
{
  "error": {
    "message": "Voice 'your-voice-name' does not support model 'qwen-tts'",
    "type": "invalid_request_error",
    "param": "voice",
    "code": "voice_binding_not_found"
  }
}
```

`type` はHTTPステータスに応じて切り替わる:

| ステータス | type |
|-----------|------|
| 4xx | `invalid_request_error` |
| 5xx | `server_error` |

## モード分岐

`VOICE_GATEWAY_MODE` 環境変数により、起動時にルートとProviderを切り替える。

| モード | 登録されるルート | Provider |
|--------|----------------|----------|
| `tts` | TTS系 + 共通（/health, /v1/models, /v1/capabilities） | TTS Providerのみ |
| `stt` | STT系 + 共通 | STT Providerのみ |
| `all` | 全ルート | 全Provider |

ルートの登録は `main.py` で `if _mode in (...)` により制御される。モードに含まれないルートはFastAPIに登録されないため、404になる。
