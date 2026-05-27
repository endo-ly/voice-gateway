# ReazonSpeech K2 Provider

[ReazonSpeech K2](https://github.com/reazon-research/ReazonSpeech) をバックエンドとして利用するSTT Providerの内部仕様。

## 概要

- Provider名: `reazonspeech_k2`
- 方向: STT
- 呼び出し方式: Python import（`asyncio.to_thread()` で非同期ラップ）
- 言語: 日本語（デフォルト）

## インストール

```bash
uv sync --group dev --extra reazonspeech-k2
./scripts/install-reazonspeech-k2.sh
```

## 設定

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

> **Note**: `precision` と `device` は未対応。将来のために予約済み。`provider_config` に追加しても無視される。

### 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `STT_VENDOR_DIR` | `.vendor` | ReazonSpeechインストールディレクトリ |

## 音声要件

- 形式: WAV（PCM）
- デフォルト最大長: 30秒
- 推奨サンプルレート: 16000 Hz
- 推奨チャンネル数: 1（モノラル）

## 制限事項

- **モデルキャッシュ**: モデルは初回使用時に遅延ロードされ、`model_id:language` キーでキャッシュされる。異なる `model_id` や `language` を指定すると新たにモデルがロードされる（初回リクエストは重い）。同じキーの後続リクエストはキャッシュを再利用する。
- **モデルのアンロードなし**: 一度ロードされたモデルはプロセスの生存期間中メモリに残る。退去・アンロードの仕組みはない。

## API使用例

### OpenAI互換

```bash
curl -X POST http://localhost:8012/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=stt-default"
```

レスポンス:
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

レスポンス:
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
