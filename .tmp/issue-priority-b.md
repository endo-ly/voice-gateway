## 概要

品質・保守性・運用性を高める優先度Bの改善をまとめる。
現状のAPIとProvider構造は安定しているため、ここでは observability、error mapping、schema方針、ログ安全性、timeout設計、CLI UX を中心に整える。

## 対応項目

### 1. `/health` を live / ready に分ける

現状の `/health` はプロセス生存確認のみで、常に `{"status":"ok"}` に近い。

追加案:

- `GET /health/live`
  - プロセス生存確認
- `GET /health/ready`
  - profile 読み込み確認
  - Provider登録確認
  - Irodori repo dir / bridge script / tmp dir の確認
  - model / voice 件数
  - 必須設定の簡易検査

### 2. `ProviderNotFoundError` / `InvalidProfileError` の ErrorMapper 対応を明示する

現状でもfallbackで500になるが、error code が `internal_error` 寄りになり、ドキュメントとの対応が曖昧になる。

- `ProviderNotFoundError` を明示的にmapする
- `InvalidProfileError` を明示的にmapする
- API error response の code を安定させる

### 3. Pydantic schema の extra handling を明示する

OpenAI互換APIで未知フィールドを拒否するか無視するかを明文化する。

候補:

- 厳格運用: `extra="forbid"`
- OpenAI互換性優先: `extra="ignore"`

互換クライアント利用を考えると、OpenAI互換エンドポイントでは `extra="ignore"` が扱いやすい。
一方で Native API は `extra="forbid"` でもよい。

### 4. request text / caption のログ出力方針を安全側に倒す

現状、Providerログに読み上げ本文やcaptionが出る箇所がある。
実運用では会話内容や個人情報が含まれる可能性がある。

- デフォルトでは全文をログに出さない
- `text_len`, `text_hash`, `model_id`, `voice_id`, `engine` 程度にする
- 必要なら `LOG_REQUEST_TEXT=true` のような設定で明示的に許可する

### 5. `timeout_sec` の責務を整理する

`ModelDefaults.timeout_sec` があるが、実際の subprocess timeout はProvider生成時の設定値に寄っている。

方針を決める:

- 環境変数の timeout だけを正とし、model defaults から削除する
- または request/model 単位で timeout をProviderへ渡す

長期的には model / provider ごとに重さが異なるため、request/model 単位 timeout が望ましい。

### 6. CLI の例外処理とUXを改善する

`app/cli/voices.py` では repository が例外を投げる前提と `None` チェックが混在している。

- `ModelNotFoundError`, `VoiceNotFoundError`, `VoiceBindingNotFoundError`, `InvalidProfileError` を明示catchする
- CLIでは traceback ではなくユーザー向けの短いエラーを出す
- batch処理時の skipped reason をわかりやすくする

## 受け入れ条件

- `uv run pytest -q` が全件成功する
- `/health/live` と `/health/ready` のテストが追加される
- `ProviderNotFoundError` / `InvalidProfileError` が安定したAPI error codeで返る
- OpenAI互換APIとNative APIのextra field方針がテストとdocsに反映される
- デフォルトログに読み上げ本文が出ない
- `timeout_sec` の設計方針が実装・docsで一致する
- CLIの主要エラーがユーザー向けメッセージとして表示される

## 備考

このissueは運用品質を上げるための束。
優先度Aの設定・Provider整備後に着手すると差分が整理しやすい。
