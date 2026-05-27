# 開発ガイド

voice-gatewayの開発環境構築、テスト、プロジェクト構成を説明する。

## 目次

1. [開発環境構築](#開発環境構築)
2. [プロジェクト構成](#プロジェクト構成)
3. [テスト](#テスト)
4. [TDD運用](#tdd運用)
5. [コーディング規約](#コーディング規約)

---

## 開発環境構築

```bash
# リポジトリをクローン
git clone https://github.com/endo-ly/voice-gateway.git && cd voice-gateway

# 依存インストール（uv が .venv を自動管理）
uv sync --group dev

# STTサポートを含む場合
uv sync --group dev --extra reazonspeech-k2
./scripts/install-reazonspeech-k2.sh

# 設定ファイルをテンプレートからコピー
cp assets/models/models.example.yaml assets/models/models.yaml
cp assets/voices/your-voice-name/profile.example.yaml assets/voices/your-voice-name/profile.yaml

# テスト実行で確認
uv run pytest tests/ -v
```

### 必要ツール

| ツール | バージョン | 用途 |
|--------|-----------|------|
| Python | 3.12+ | 実行環境 |
| uv | 0.9+ | パッケージ管理・仮想環境管理 |
| pytest | 9+ | テストランナー |
| pytest-asyncio | 1.3+ | 非同期テスト |
| httpx | 0.28+ | AsyncClient（APIテスト） |

---

## プロジェクト構成

```
voice-gateway/
  app/
    api/                     # API層: HTTP入出力
      routes/                #   エンドポイント
        health.py            #     GET /health
        models.py            #     GET /v1/models
        capabilities.py      #     GET /v1/capabilities
        voices.py            #     GET /v1/voices (tts/all)
        openai_speech.py     #     POST /v1/audio/speech (tts/all)
        native_speech.py     #     POST /v1/speech (tts/all)
        openai_transcriptions.py  # POST /v1/audio/transcriptions (stt/all)
        transcriptions.py    #     POST /v1/transcribe (stt/all)
        transcriptions_latest.py  # GET /v1/transcribe/latest (stt/all)
      schemas/               #   リクエスト/レスポンス定義
        openai_speech.py     #     OpenAISpeechRequest
        native_speech.py     #     NativeSpeechRequest
        transcription.py     #     TranscriptionRequest / TranscriptionResultSchema
        capabilities.py      #     CapabilitiesResponse
        error.py             #     ErrorResponse
      dependencies.py        #   FastAPI依存注入

    application/             # Application層: ユースケース・サービス
      use_cases/
        synthesize_speech.py #     TTS 音声合成ユースケース
        transcribe_audio.py  #     STT 音声認識ユースケース
        get_latest_transcription.py  # 直近転写結果取得
        list_models.py       #     model一覧取得
        list_voices.py       #     voice一覧取得
      services/
        model_resolver.py    #     model解決（共通）
        option_merger.py     #     5層設定マージ（共通）
        error_mapper.py      #     domain error → HTTP（共通）
        tts_profile_resolver.py   # TTS model + voice 解決
        tts_provider_registry.py  # TTS Provider lookup
        stt_profile_resolver.py   # STT model 解決
        stt_provider_registry.py  # STT Provider lookup

    domain/                  # Domain層: 中核概念（依存なし）
      entities/
        model_profile.py     #     ModelProfile (direction付き)
        stt_model_defaults.py #    STTModelDefaults
        voice_profile.py     #     VoiceProfile
      value_objects/
        synthesis_request.py #     ProviderSynthesisRequest (TTS)
        synthesis_result.py  #     SynthesisResult (TTS)
        transcription_request.py  # TranscriptionRequest (STT)
        transcription_result.py   # TranscriptionResult (STT)
      interfaces/
        tts_provider.py      #     TTSProvider Protocol
        stt_provider.py      #     STTProvider Protocol
        model_profile_repository.py
        voice_profile_repository.py
        transcription_store.py
      errors.py              #     domain error群

    infrastructure/          # Infrastructure層: 実装
      config/
        settings.py          #     pydantic-settings (VOICE_GATEWAY_MODE)
      repositories/
        yaml_model_profile_repository.py  # YAML読み込み (ModelProfile)
        yaml_voice_profile_repository.py  # YAML読み込み (VoiceProfile)
        in_memory_transcription_store.py  # 転写結果インメモリ保持
      providers/
        fake/provider.py     #     テスト用ダミーTTS Provider
        irodori/             #     Irodori CLI subprocess (TTS)
          provider.py        #       Provider本体（Semaphore付き）
          cli_builder.py     #       CLI引数組み立て
          subprocess_runner.py
          config_schemas.py
          latent_encoder.py  #       WAV→PT変換
        reazonspeech_k2/     #     ReazonSpeech K2 (STT)
          provider.py        #       Provider本体（マルチモデルキャッシュ付き）
          audio_validator.py #       音声バリデーション
          types.py           #       内部型定義
      events/
        stt_callback_dispatcher.py  # 転写結果コールバック送信
      tempfiles/
        manager.py           #     UUID付きtmpファイル管理
      logging/
        logger.py            #     logging設定

    main.py                  # FastAPI app組み立て・DI・モード分岐

  scripts/
    irodori_encode_latent.py #     Irodori環境内で動くエンコード用ブリッジスクリプト
    install-reazonspeech-k2.sh

  assets/                    # 設定ファイル（.gitignoreで管理）
    models/
      models.example.yaml    #   テンプレート
      models.yaml            #   実際の設定（gitignore）
    voices/
      your-voice-name/
        profile.example.yaml
        profile.yaml
        ref.wav               #   参照音声（gitignore）
        ref_latent.pt         #   バイナリ（gitignore）

  tests/                     # テストコード
    conftest.py              #   セッションスコープ: .example.yaml → .yaml コピー
    domain/                  #   Domain層テスト
    infrastructure/          #   Infrastructure層テスト
    application/             #   Application層テスト
    api/                     #   API層テスト
    integration/             #   統合テスト

  docs/                      # ドキュメント
  tmp/                       # 一時ファイル出力先
  pyproject.toml             # プロジェクト設定
  .env.example               # 環境変数テンプレート
```

---

## テスト

### 実行コマンド

```bash
# 全テスト
uv run pytest tests/ -v

# 層ごと
uv run pytest tests/domain/ -v
uv run pytest tests/infrastructure/ -v
uv run pytest tests/application/ -v
uv run pytest tests/api/ -v
uv run pytest tests/integration/ -v

# ファイル指定
uv run pytest tests/domain/test_errors.py -v

# 詳細表示
uv run pytest tests/ -v --tb=long
```

### テスト構成

| 層 | テスト数 | 内容 |
|----|---------|------|
| Domain | — | Pydantic validation、Protocol適合性、errorのフィールド、TTS/STT defaults |
| Infrastructure | — | YAML読み込み、FakeProvider、Irodori CLI組み立て、subprocess実行、ReazonSpeech K2 Provider、audio_validator、transcription_store、callback_dispatcher |
| Application | — | 設定マージ、Provider lookup、profile解決、errorマッピング、ユースケース |
| API | — | schema validation、エンドポイントのstatus code・content-type・モード分岐 |
| Integration | — | 受け入れ条件のEnd-to-End検証 |
| **Total** | **263** | |

### conftest.py

`tests/conftest.py` はセッションスコープのfixtureで、テスト実行前に `.example.yaml` から実際のYAMLファイルを自動生成する。テスト終了後に削除する。

---

## TDD運用

このプロジェクトは **ボトムアップTDD** で開発している。

### サイクル

```
1. テストを書く（Red）
2. 最小実装を書く（Green）
3. リファクタする（Refactor）
```

### 実装順序

```
Domain（依存なし）→ Infrastructure → Application → API → Integration
```

内側の層から先にテスト・実装を固めることで、外側の層のテストは内側のモック・スタブを使わずに書ける。

### 新機能追加時の例

QwenTTSProviderを追加する場合:

1. `tests/infrastructure/qwen_tts/test_provider.py` を書く
2. `app/infrastructure/providers/qwen_tts/provider.py` を実装する
3. テストが通ることを確認する
4. `assets/models/models.yaml` にmodelを追加する
5. 各voiceにbindingを追加する
6. 統合テストで確認する

---

## 管理CLI

WAV→PT変換など、音声合成以外の管理操作はCLIで行う。

```bash
# ref.wav から ref_latent.pt を生成
uv run python -m app.cli voices build-ref-latent \
  --voice-id your-voice-name \
  --model-id tts-default

# 生成ついでに profile.yaml に ref_latent_path を書き込む
uv run python -m app.cli voices build-ref-latent \
  --voice-id your-voice-name \
  --model-id tts-default \
  --write-profile

# 一括移行: 全voiceのref.wavをref_latent.ptに変換
uv run python -m app.cli voices materialize-ref-latents \
  --all \
  --model-id tts-default \
  --write-profile

# 特定voiceだけ一括移行
uv run python -m app.cli voices materialize-ref-latents \
  --voice-id your-voice-name \
  --model-id tts-default \
  --write-profile
```

## コーディング規約

- **型アノテーション**: 全関数・メソッドに型を付ける。`as any`、`@ts-ignore` 等の型抑制は禁止
- **エラー処理**: `VoiceGatewayError` のサブクラスを使う。`except Exception` は避ける
- **YAML**: `safe_load` を使う。読み込み後はPydanticでvalidationする
- **subprocess**: `shell=True` 禁止。`list[str]` で引数を組み立てる
- **非同期**: `async def` を使う。`asyncio.Semaphore` で同時実行数を制限する
- **tmpファイル**: UUID付きで作成し、bytes読み込み後に削除する
- **コメント**: コードが自明であれば書かない。必要な場合のみ（複雑なアルゴリズム、セキュリティ、正規表現等）
