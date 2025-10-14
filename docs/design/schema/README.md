# スキーマ管理ガイド

このディレクトリは pptx_generator パイプラインで扱う JSON スキーマを集約する。  
工程別の利用シーンに応じてファイルを分割し、仕様変更の追跡とテスト連携を容易にする。

## ファイル構成
- `overview.md`: スキーマ全体の目的と横断的な拡張ポイント。
- `content.md`: 工程3で扱う `content_draft.json` / `content_approved.json` の仕様。
- `draft.md`: 工程4の `draft_draft.json` / `draft_approved.json` の仕様。
- `mapping.md`: 工程5の `rendering_ready.json` / `mapping_log.json` の仕様。
- `rendering.md`: 工程6の `rendering_log.json` / `audit_log.json` の仕様。
- `changelog.md`: スキーマ変更履歴。
- `samples/`: 代表的な JSON サンプル（`.jsonc`）。

## 運用ルール
- スキーマを変更した場合は、対応する `*.md` と `changelog.md` を更新し、必要に応じてサンプルも更新する。
- 実装（`pptx_generator/models.py`）とテスト（`tests/` 配下）を同時に調整すること。
- スキーマ追加時は stage ドキュメントからリンクし、参照先を明示する。

## 更新手順
1. 変更内容と影響範囲を洗い出す（関連工程・モジュール・テスト）。
2. 対応するスキーマファイルを修正し、サンプル JSON を更新。
3. `changelog.md` にエントリを追加し、ToDo / Roadmap に必要なタスクを登録。
4. CI でスキーマ検証・テストを通し、レビュー観点をまとめる。
