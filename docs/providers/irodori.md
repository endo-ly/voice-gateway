# Irodori-TTS Provider

[Irodori-TTS](https://github.com/Aratako/Irodori-TTS) をバックエンドとして利用するProviderの内部仕様。
voice-gatewayがIrodoriをどのように呼び出しているかを説明する。

## 呼び出し方式

Irodoriは **server** と **CLI** の2つのbackendを持つ。`IRODORI_BACKEND` 環境変数で切り替える（デフォルト: `server`）。

| 値 | 方式 | 説明 |
|------|------|------|
| `server`（デフォルト） | Irodori-TTS-Server（HTTP） | Gateway内部HTTP Engineとして管理起動し、HTTP APIで呼び出す |
| `cli` | CLIサブプロセス | `infer.py` をsubprocess実行する。比較・デバッグ用途 |

### server backend（デフォルト）

[Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server) をGateway内部HTTP Engineとして扱う。
`IRODORI_MANAGE_SERVER=true` の場合、Gateway起動時にIrodori-TTS-Serverをsubprocessで起動し、`/health` が応答するまで待つ。

```
voice-gateway (IrodoriProvider → IrodoriServerClient)
  │
  │  POST {IRODORI_SERVER_BASE_URL}/v1/audio/speech
  │  body = { model, input, voice, response_format, irodori: {...} }
  │
  ▼
Irodori-TTS-Server
  │ Irodori runtimeは常駐（モデルロード1回のみ）
  │ リクエストごとに推論 → audio/wav bytesを返却
  ▼
voice-gateway
  │ response.content を SynthesisResult として返す
  ▼
client (audio/wav)
```

#### サーバーリクエスト形式

```json
{
  "model": "irodori-tts",
  "voice": null,
  "input": "こんにちは。",
  "response_format": "wav",
  "irodori": {
    "chunking_enabled": false,
    "ref_wav": "/absolute/path/to/ref.wav",
    "ref_latent": null,
    "num_steps": 28,
    "seed": 0,
    "speaker_kv_scale": 1.0
  }
}
```

| フィールド | 出処 | 説明 |
|------------|------|------|
| `model` | 固定値 `"irodori-tts"` | Irodori-TTS-Serverに渡すmodel名 |
| `voice` | provider_config (`voice`) | voice名。通常は `null`（ref_wav/ref_latentで指定） |
| `input` | リクエスト | 読み上げるテキスト |
| `response_format` | リクエスト | `wav` |
| `irodori.chunking_enabled` | 固定 `false` | Gateway側でチャンキングするため、サーバー側はOFF |
| `irodori.ref_wav` | provider_config (`ref_wav_path`) | 参照音声のWAVパス |
| `irodori.ref_latent` | provider_config (`ref_latent_path`) | 参照音声のlatent tensorパス（ref_wavより優先） |
| `irodori.num_steps` | provider_config | 推論ステップ数。デフォルト28 |
| `irodori.seed` | provider_config | 乱数シード。デフォルト0 |
| `irodori.speaker_kv_scale` | provider_config | 話者特徴の強さ。デフォルト1.0 |

CLI backendとの違い:
- `checkpoint`, `model_device`, `codec_device`, `model_precision`, `codec_precision` はサーバー側で管理されるため送信しない
- `ref_wav_path` → `irodori.ref_wav`, `ref_latent_path` → `irodori.ref_latent` にキー名を変換
- `max_text_len`, `max_caption_len` はサーバー側で管理されるため送信しない

### CLI backend（デバッグ用途）

voice-gatewayは `IRODORI_REPO_DIR` を `cwd` にして `uv run --no-sync python infer.py` を実行する。
Irodori-TTSリポジトリの `infer.py` が実際の推論を行い、結果をWAVファイルに書き出す。

```
voice-gateway (IrodoriProvider → IrodoriCliClient)
  │
  │  cwd = $IRODORI_REPO_DIR
  │  argv = ["uv", "run", "--no-sync", "python", "infer.py", "--hf-checkpoint", ...]
  │
  ▼
Irodori-TTS/infer.py
  │ 推論を実行
  │ --output-wav で指定したパスにWAVを書き出す
  ▼
voice-gateway
  │ WAVを読み込んでbytesとして返す
  │ tmpファイルを削除
  ▼
client (audio/wav)
```

## 前提条件

### 共通

| 項目 | デフォルト | 説明 |
|------|-----------|------|
| `IRODORI_REPO_DIR` | `.vendor/Irodori-TTS` | Irodori-TTSリポジトリのルートパス（`infer.py`が存在するディレクトリ） |
| チェックポイント | — | HuggingFaceのrepo ID（初回は自動ダウンロード） |

### セットアップ

```bash
# server backend（デフォルト）: Irodori-TTS-Serverのみ
./scripts/install-irodori-tts-server.sh       # Linux/macOS
./scripts/install-irodori-tts-server.ps1      # Windows

# CLI backend / ref_latentエンコード: Irodori-TTSのみ
./scripts/install-irodori-tts.sh              # Linux/macOS
./scripts/install-irodori-tts.ps1             # Windows

# PyTorch backendを指定（デフォルト: cu128）
IRODORI_TORCH_BACKEND=rocm ./scripts/install-irodori-tts-server.sh
$env:IRODORI_TORCH_BACKEND="rocm"; ./scripts/install-irodori-tts-server.ps1
```

`--no-sync` フラグ付きで `uv run` を実行するため、`uv sync --extra <backend>` で事前インストールが必要。

### server backend追加要件

| 項目 | デフォルト | 説明 |
|------|-----------|------|
| `IRODORI_SERVER_DIR` | `.vendor/Irodori-TTS-Server` | Irodori-TTS-Serverリポジトリのルートパス |
| `IRODORI_SERVER_BASE_URL` | `http://127.0.0.1:18790` | Gatewayから接続するURL |
| Irodori-TTS-Server側 | — | `uv sync` 済みであること |

### CLI backend追加要件

| 項目 | 値 |
|------|---|
| Irodori-TTS側の依存 | `uv sync` 済みであること |

## CLI コマンド引数

### base engine（ゼロショット音声クローン）

参照音声から声をコピーして推論する。`engine: base` の場合に使用。

```
uv run --no-sync python infer.py \
  --hf-checkpoint <checkpoint> \
  --text <text> \
  --ref-latent <ref_latent_path> \
  --output-wav <output_wav_path> \
  --num-steps <num_steps> \
  --seed <seed> \
  --speaker-kv-scale <speaker_kv_scale> \
  --model-device <model_device> \
  --codec-device <codec_device> \
  --model-precision <model_precision> \
  --codec-precision <codec_precision>
```

| 引数 | 型 | 出処 | 説明 |
|------|----|------|------|
| `--hf-checkpoint` | str | ModelProfile.provider_config | HuggingFaceのチェックポイントrepo ID |
| `--text` | str | リクエスト | 読み上げるテキスト |
| `--ref-latent` | str | VoiceBinding.provider_config | 参照音声のlatent tensor（.pt）。`--ref-wav` より優先 |
| `--ref-wav` | str | VoiceBinding.provider_config | 参照音声のWAVファイル。`--ref-latent` が無い場合に使用 |
| `--output-wav` | str | 内部生成（tmp） | 出力先WAVパス。推論後に読み込んで削除 |
| `--num-steps` | int | VoiceBinding.provider_config | 推論ステップ数。デフォルト28 |
| `--seed` | int | VoiceBinding.provider_config | 乱数シード。デフォルト0 |
| `--speaker-kv-scale` | float | VoiceBinding.provider_config | 話者特徴の強さ。デフォルト1.0 |
| `--model-device` | str | ModelProfile.provider_config | モデル推論デバイス（`cpu` / `cuda`） |
| `--codec-device` | str | ModelProfile.provider_config | コーデック推論デバイス（`cpu` / `cuda`） |
| `--model-precision` | str | ModelProfile.provider_config | モデル精度（`fp32` / `bf16`） |
| `--codec-precision` | str | ModelProfile.provider_config | コーデック精度（`fp32` / `bf16`） |

`--ref-latent` と `--ref-wav` はどちらか一方が必須。両方ある場合は `--ref-latent` が使われる。

### voicedesign engine（キャプション条件付き音声設計）

テキストによる声の特徴の指定だけで推論する。参照音声不要。`engine: voicedesign` の場合に使用。

```
uv run --no-sync python infer.py \
  --hf-checkpoint <checkpoint> \
  --text <text> \
  --caption <caption> \
  --no-ref \
  --output-wav <output_wav_path> \
  --num-steps <num_steps> \
  --seed <seed> \
  --model-device <model_device> \
  --codec-device <codec_device> \
  --model-precision <model_precision> \
  --codec-precision <codec_precision>
```

base engineとの違い:

| 項目 | base | voicedesign |
|------|------|-------------|
| 参照音声 | `--ref-latent` / `--ref-wav` 必須 | `--no-ref`（参照なし） |
| キャプション | なし | `--caption` で声の特徴を指定 |
| `--speaker-kv-scale` | あり | なし |
| チェックポイント | `Irodori-TTS-500M-v2` | `Irodori-TTS-500M-v2-VoiceDesign` |

## 設定の出処（5層マージ）

provider_config は5層の設定をマージして決定する。後の層が前の層を上書きする。

```
1. ModelProfile.defaults      ← models.yaml の defaults
2. VoiceProfile.defaults      ← profile.yaml の defaults
3. ModelProfile.provider_config ← models.yaml の provider_config
4. VoiceBinding.provider_config ← profile.yaml の bindings[model_id].provider_config
5. Request options             ← APIリクエストのパラメータ（将来拡張）
```

実運用では、ModelProfileにデバイスや精度などの共通設定を置き、VoiceBindingに各声ごとの `ref_latent_path`・`seed`・`speaker_kv_scale` を置く。

### 具体例: マージ結果

**ModelProfile** (`models.yaml`):
```yaml
provider_config:
  checkpoint: Aratako/Irodori-TTS-500M-v2
  model_device: cuda
  codec_device: cuda
  model_precision: fp32
  codec_precision: fp32
  max_text_len: 1024
  max_caption_len: 1024
```

**VoiceBinding** (`profile.yaml`):
```yaml
bindings:
  tts-default:
    provider_config:
      ref_latent_path: assets/voices/your-voice-name/ref_latent.pt
      seed: 42
      num_steps: 28
      speaker_kv_scale: 1.0
```

**マージ後の provider_config**:
```yaml
checkpoint: Aratako/Irodori-TTS-500M-v2
model_device: cuda
codec_device: cuda
model_precision: fp32
codec_precision: fp32
max_text_len: 1024
max_caption_len: 1024
ref_latent_path: assets/voices/your-voice-name/ref_latent.pt
seed: 42
num_steps: 28
speaker_kv_scale: 1.0
```

このマージ済みconfigが `IrodoriProvider` に渡り、コマンド引数に展開される。

## WAV→PT事前変換

base engineでは `ref_wav_path` でも動くが、毎回WAVをエンコードするオーバーヘッドがある。
`ref_latent_path`（.pt）を事前に生成しておくと、推論時のエンコード処理がスキップされる。

### 変換コマンド

```bash
# 単一voiceの変換
uv run python -m app.cli voices build-ref-latent \
  --voice-id your-voice-name \
  --model-id tts-default

# profile.yamlにも書き込む場合
uv run python -m app.cli voices build-ref-latent \
  --voice-id your-voice-name \
  --model-id tts-default \
  --write-profile

# 全voiceを一括変換
uv run python -m app.cli voices materialize-ref-latents \
  --all \
  --model-id tts-default \
  --write-profile
```

### 内部の仕組み

変換時は `scripts/irodori_encode_latent.py` というブリッジスクリプトをIrodori環境内で実行する。

```
voice-gateway (IrodoriLatentEncoder)
  │
  │  cwd = $IRODORI_REPO_DIR
  │  argv = ["uv", "run", "--no-sync", "python", "scripts/irodori_encode_latent.py", ...]
  │
  ▼
scripts/irodori_encode_latent.py
  │ 1. IrodoriのDACVAECodecをロード
  │ 2. ref.wavを読み込んでPCMにデコード
  │ 3. codec.encode_waveform() でlatent tensorを生成
  │ 4. torch.save() で .pt ファイルに保存
  ▼
ref_latent.pt 生成完了
```

ブリッジスクリプトのコマンド引数:

```
uv run --no-sync python scripts/irodori_encode_latent.py \
  --input-wav <ref_wav_path> \
  --output-pt <output_pt_path> \
  --checkpoint <checkpoint> \
  --codec-repo Aratako/Semantic-DACVAE-Japanese-32dim \
  --model-device <model_device> \
  --codec-device <codec_device> \
  --model-precision <model_precision> \
  --codec-precision <codec_precision>
```

## 実行制御

### 共通

| 項目 | 値 | 説明 |
|------|---|------|
| 同時実行数 | 1（Semaphore） | GPUリソースの競合を防ぐため、Irodoriの推論は同時に1リクエストのみ |
| タイムアウト | 120秒（デフォルト） | `TIMEOUT_SEC` 環境変数で変更可能。超過すると `ProviderTimeoutError` (504) |

### CLI backendのみ

| 項目 | 値 | 説明 |
|------|---|------|
| tmpファイル | UUIDベースのWAVパス | `tmp/` に生成。読み込み後に必ず削除（finally ブロック） |

### server backendのみ

| 項目 | 値 | 説明 |
|------|---|------|
| 管理起動 | `IRODORI_MANAGE_SERVER=true` 時にGateway起動時にsubprocess起動 | `irodori_tts_server_process.py` が `ManagedHttpEngineProcess` を生成 |
| 起動待ち | `/health` が200を返すまで待機 | timeoutは `IRODORI_SERVER_STARTUP_TIMEOUT_SEC`（デフォルト300秒） |
| 二重起動防止 | 既に `/health` が応答する場合は新規起動しない | 外部で起動済みのIrodori-TTS-Serverを再利用 |
| 停止 | Gateway停止時にプラットフォーム固有の終了シグナル送信（Unix: SIGTERM→SIGKILL、Windows: CTRL_BREAK→taskkill） | `ManagedHttpEngineProcess.stop()` が実行 |

## エラーハンドリング

### 共通

| 状況 | 例外 | HTTP |
|------|------|------|
| プロセスがタイムアウト | `ProviderTimeoutError` | 504 |
| 推論失敗 | `ProviderExecutionError` | 500 |

### CLI backend

| 状況 | 例外 | HTTP |
|------|------|------|
| プロセスが非ゼロexit code | `ProviderExecutionError`（stderrを含む） | 500 |
| 出力WAVが存在しない | `ProviderExecutionError("Output WAV file was not created")` | 500 |
| 出力WAVが空 | `ProviderExecutionError("Output WAV file is empty")` | 500 |

### server backend

| 状況 | 例外 | HTTP |
|------|------|------|
| Irodori-TTS-ServerがHTTPエラー | `ProviderExecutionError`（status code + body） | 500 |
| Irodori-TTS-Serverが空レスポンス | `ProviderExecutionError("empty audio")` | 500 |
| 接続失敗（サーバー未起動） | `ProviderExecutionError` | 500 |
| サーバー起動タイムアウト | Gateway起動失敗（`RuntimeError`） | — |

## 関連ファイル

| ファイル | 役割 |
|----------|------|
| `app/infrastructure/providers/irodori/provider.py` | Provider本体。backend切替（server/cli）とsemaphore制御 |
| `app/infrastructure/providers/irodori/server_client.py` | Irodori-TTS-Server HTTP呼び出しクライアント（server backend） |
| `app/infrastructure/providers/irodori/cli_client.py` | CLI subprocess呼び出しクライアント（cli backend） |
| `app/infrastructure/providers/irodori/cli_builder.py` | CLIコマンド引数のlist[str]組み立て |
| `app/infrastructure/providers/irodori/subprocess_runner.py` | asyncio.create_subprocess_exec のラッパー |
| `app/infrastructure/providers/irodori/config_schemas.py` | provider_config validation（`IrodoriBaseConfig`, `IrodoriServerBaseConfig`, `IrodoriVoiceDesignConfig`） |
| `app/infrastructure/runtime/irodori_tts_server_process.py` | Irodori-TTS-Server管理起動のfactory（`ManagedHttpEngineProcess`） |
| `app/infrastructure/providers/irodori/latent_encoder.py` | WAV→PT変換の実行 |
| `scripts/irodori_encode_latent.py` | Irodori環境内で動くエンコード用ブリッジスクリプト |
| `app/cli/voices.py` | `build-ref-latent` / `materialize-ref-latents` CLIコマンド |
| `app/infrastructure/config/settings.py` | `IRODORI_BACKEND`, `IRODORI_SERVER_*` の読み込みとパス正規化 |
