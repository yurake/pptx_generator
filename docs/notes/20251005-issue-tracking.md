# 2025-10-05 Issue 作成漏れの振り返り

## 事象
- `docs/todo/20251005-rules-branding-tests.md` の更新時に `関連Issue: #2` と記載したが、GitHub 上に Issue #2 は存在していなかった。
- `gh issue comment 2` を実行した際、Issue ではなく PR #2 にコメントしていた。

## 原因
- 既存 ToDo に書かれていた `#2` を実在すると誤認し、実際の Issue 一覧を確認しなかった。
- PR と Issue で番号が重複するケースを考慮せず、`gh issue comment` の結果を十分に検証しなかった。

## 対応
- 正しい Issue (#3) を新規作成し、ToDo を更新。
- 以下の運用ルールを追加。
  - Issue 番号を記載する前に `gh issue list --state all` で存在を確認する。
  - `gh issue comment` 実行後に URL を必ず確認し、PR へのコメントになっていないか検証する。

## 未対応項目
- テンプレートと README を改訂し、上記確認手順を明文化する（別途対応中）。
