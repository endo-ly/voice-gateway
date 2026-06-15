# AivisSpeech Provider

[AivisSpeech Engine](https://github.com/Aivis-Project/AivisSpeech-Engine) をバックエンドとして利用するTTS Providerの内部仕様。

## 概要

- Provider名: `aivis_speech`
- 方向: TTS
- Engine: `voicevox-compatible`
- 呼び出し方式: HTTP API
- 管理起動: 任意。`AIVIS_MANAGE_ENGINE=true` の場合、voice-gatewayのlifespanでEngineを起動・停止する

## 動作環境

| モード | 環境 | 備考 |
|--------|------|------|
| 管理起動 (`AIVIS_MANAGE_ENGINE=true`) | Linux | プロセス管理に `os.killpg` / `SIGTERM` / `SIGKILL` を使用 |
| 外部Engine (`AIVIS_MANAGE_ENGINE=false`) | Linux / Windows | 別途起動したEngineにHTTP接続のみ |

## 動的voice発見

Engine自身がspeaker/style一覧を管理するため、voice-gatewayは起動時に `/speakers` をフェッチして各speaker/styleをvoiceとして登録する。`assets/voices/` にprofile.yamlを置く必要はない。

### 仕組み

1. lifespanでAivisSpeech Engineの起動完了を待つ
2. `AivisSpeechProvider.list_speakers()` で `/speakers` をGET
3. `speaker_sync.speakers_to_voice_profiles()` で各speaker/styleを `VoiceProfile` に変換
4. `YamlVoiceProfileRepository.register()` でvoice_repoに追加
5. フェッチ失敗時はWARNログで継続（静的profileだけで稼働）

実装は `app/infrastructure/providers/aivis_speech/speaker_sync.py`。

### voice IDの規約

| パターン | 意味 | 例 |
|---------|------|------|
| `<speaker_name>` | デフォルトstyle（"ノーマル"優先、なければ最初のstyle） | `まお`, `コハク` |
| `<speaker_name>/<style_name>` | 個別style | `まお/あまあま`, `コハク/せつなめ` |

`display_name` はデフォルトstyleが `<speaker_name>`、個別styleが `<speaker_name> (<style_name>)`。各voiceは `bindings["aivis-default"].provider_config = {"speaker": <style_id>}` を持つ。

### 静的profileとの関係

後方互換のため、`assets/voices/your-voice-name/profile.yaml` のようなAivisSpeech用の静的profileも引き続き機能する。ただし新規設定では不要。静的profileと動的voiceでvoice_idが衝突した場合は静的が優先される。

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
      output_sampling_rate: 24000
      output_stereo: false
```

**注意:** `speaker` はModelの `provider_config` には含めず、Voice Profile側のbindingで指定する。これにより声の識別子を論理ID（voice_id）で管理するGatewayの思想に合致する。

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
| `AIVIS_BASE_URL` | `http://127.0.0.1:10101` | AivisSpeech EngineのURL（Gatewayが接続する先） |
| `AIVIS_MANAGE_ENGINE` | `false` | `true` の場合、voice-gateway起動時にAivisSpeech Engineも起動する |
| `AIVIS_ENGINE_DIR` | `.vendor/AivisSpeech-Engine` | 管理起動するAivisSpeech Engineのディレクトリ |
| `AIVIS_ENGINE_BIND_HOST` | — | Engine起動時のバインドホスト（未設定時は`AIVIS_BASE_URL`のhostnameを使用） |
| `AIVIS_ENGINE_PORT` | — | Engine起動時のポート（未設定時は`AIVIS_BASE_URL`のポートを使用） |
| `AIVIS_USE_GPU` | `false` | `true` の場合、Engine起動時に`--use_gpu`を使用する |
| `AIVIS_STARTUP_TIMEOUT_SEC` | `180` | AivisSpeech Engine起動待ちタイムアウト（秒） |

`AIVIS_ENGINE_BIND_HOST` / `AIVIS_ENGINE_PORT` は `AIVIS_MANAGE_ENGINE=true` の場合のみ使用される。Docker・Tailscale・WSL等で接続先URLとバインドアドレスが異なる場合に設定する。

## 管理起動

`AIVIS_MANAGE_ENGINE=true` にすると、voice-gatewayは起動時に `AIVIS_BASE_URL` の `/version` を確認する。すでにEngineが応答していれば新しいプロセスは起動しない。応答がない場合は `AIVIS_ENGINE_DIR` で以下を実行する。

```bash
uv run run.py --host <bind_host> --port <port> <--use_gpu|--no-use_gpu> --output_log_utf8
```

終了時は起動したプロセスグループにSIGTERMを送り、一定時間で終了しない場合はSIGKILLする。

## ヘルスチェック

`/health` エンドポイントでAivisSpeech Engineの到達可能性を確認する。Providerが `engineReachable: true/false` を返すため、外部Engine接続時に実際の死活を把握できる。

```json
{
  "providers": {
    "tts": {
      "aivis_speech": {
        "registered": true,
        "loaded": true,
        "engineReachable": true,
        "baseUrl": "http://127.0.0.1:10101"
      }
    }
  }
}
```

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
