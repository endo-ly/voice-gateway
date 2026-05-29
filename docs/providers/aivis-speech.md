# AivisSpeech Provider

[AivisSpeech Engine](https://github.com/Aivis-Project/AivisSpeech-Engine) をバックエンドとして利用するTTS Providerの内部仕様。

## 概要

- Provider名: `aivis_speech`
- 方向: TTS
- Engine: `voicevox-compatible`
- 呼び出し方式: HTTP API
- 管理起動: 任意。`AIVIS_MANAGE_ENGINE=true` の場合、voice-gatewayのlifespanでEngineを起動・停止する

## 設定

### models.yaml

```yaml
models:
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
```

### voice profile

```yaml
bindings:
  aivis-default:
    provider_config:
      speaker: 888753760
```

`speaker` はAivisSpeech Engineのspeaker/style ID。`speaker_id` も受け付けるが、両方ある場合は `speaker` を優先する。

### 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `AIVIS_BASE_URL` | `http://127.0.0.1:10101` | AivisSpeech EngineのURL |
| `AIVIS_MANAGE_ENGINE` | `false` | `true` の場合、voice-gateway起動時にAivisSpeech Engineも起動する |
| `AIVIS_ENGINE_DIR` | `.vendor/AivisSpeech-Engine` | 管理起動するAivisSpeech Engineのディレクトリ |
| `AIVIS_STARTUP_TIMEOUT_SEC` | `180` | AivisSpeech Engine起動待ちタイムアウト（秒） |

## 管理起動

`AIVIS_MANAGE_ENGINE=true` にすると、voice-gatewayは起動時に `AIVIS_BASE_URL` の `/version` を確認する。すでにEngineが応答していれば新しいプロセスは起動しない。応答がない場合は `AIVIS_ENGINE_DIR` で以下を実行する。

```bash
uv run run.py --host <AIVIS_BASE_URLのhost> --port <AIVIS_BASE_URLのport> --no-use_gpu --output_log_utf8
```

終了時は起動したプロセスグループにSIGTERMを送り、一定時間で終了しない場合はSIGKILLする。

## API使用例

```bash
curl -X POST http://127.0.0.1:8012/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"aivis-default","voice":"your-voice-name","input":"こんにちは"}' \
  --output output.wav
```

## 出力形式

AivisSpeech Engineから返るWAVをそのまま返す。StackChanなど24kHz monoを期待する再生先では、`provider_config` に以下を指定する。

```yaml
provider_config:
  output_sampling_rate: 24000
  output_stereo: false
```
