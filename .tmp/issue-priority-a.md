## 概要

実運用前に解消したい優先度Aの改善をまとめる。
現状はテストも通っており基本構造は安定しているが、設定と実装の不一致、リクエストオプションの未反映、Provider設定検証の遅さなどが運用事故につながる可能性がある。

## 背景

調査時点で `uv run pytest -q` は全件成功している。
一方で、ドキュメントや設定として存在する設計意図の一部が実装に十分反映されていない。

## 対応項目

### 1. `MAX_CONCURRENCY` を IrodoriProvider に反映する

- `Settings.max_concurrency` は存在するが、`IrodoriProvider` 側は `asyncio.Semaphore(1)` 固定になっている
- `IrodoriProvider.__init__` に `max_concurrency` を追加する
- `app/main.py` から `settings.max_concurrency` を渡す
- デフォルトはGPUメモリ保護のため `1` のままでよい

### 2. `ProfileResolver` と `OptionMerger` の責務を整理する

- `SynthesizeSpeech` は `option_merger` を受け取るが実質未使用
- `ProfileResolver` は `OptionMerger.merge()` を直接呼んでいる
- 依存注入の形と実責務を一致させる
- 推奨: `ProfileResolver` に `OptionMerger` を注入し、将来のmerge rule拡張に備える

### 3. request options を5層マージに実際に流す

ドキュメント上の優先度は以下。

1. model defaults
2. voice defaults
3. model provider_config
4. voice bindings
5. request overrides

現状 `ProfileResolver.resolve()` では `request_options={}` 固定になっている。

- `ProfileResolver.resolve(model_id, voice_id, request_options=None)` に変更する
- `SynthesizeSpeech.execute()` から `speed`, `response_format` などを渡す
- Native API の `style_hints` も将来利用できる形で渡す

### 4. Voice profile の重複検証を追加する

- Model profile にはID重複チェックがある
- Voice profile 側にも `voice_id` 重複チェックを追加する
- 可能なら voice profile のディレクトリ名と `voice_id` の一致も検証する

### 5. Irodori provider_config の schema validation を追加する

現状は `cfg["checkpoint"]`, `cfg["caption"]` などの参照がProvider実行時まで遅延する。
設定ミスが `KeyError` や500に近い形で出る可能性がある。

- `IrodoriBaseConfig` / `IrodoriVoiceDesignConfig` のようなPydantic schemaを追加する
- `checkpoint`, `ref_latent_path` / `ref_wav_path`, `caption` などを明示検証する
- 設定不備はProvider実行前に domain/application error として扱う

### 6. FastAPI dependency injection を整理する

現状 route 内で `from app.main import get_synthesize_speech` のように戻っている箇所がある。

- `Depends` を使った依存注入に寄せる
- `app/api/dependencies.py` などへ切り出す
- route と application bootstrap の結合を下げる

## 受け入れ条件

- `uv run pytest -q` が全件成功する
- `MAX_CONCURRENCY` の設定値がProviderのsemaphoreに反映される
- request override が `OptionMerger` の第5層として反映される
- voice profile の `voice_id` 重複時に明確な validation error になる
- Irodori provider_config 不備がProvider実行前に明確な error として返る
- 既存APIの後方互換性が維持される

## 備考

まずは小さなPRに分けてよい。
ただし、設定と実装の不一致は優先して解消する。
