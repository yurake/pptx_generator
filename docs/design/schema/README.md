# スキーマ管理ガイド

このディレクトリは pptx_generator パイプラインで扱う JSON スキーマを集約する。  
工程別の利用シーンに応じてファイルを分割し、仕様変更の追跡とテスト連携を容易にする。

## ファイル構成
- `stage-01-template-preparation.md`: テンプレ受け渡しメタ (`template_release.json` など)。
- `stage-02-template-structure-extraction.md`: `layouts.jsonl`, `diagnostics.json`, 差分レポート。
- `stage-03-content-normalization.md`: `content_draft.json`, `content_approved.json`, 承認ログ。
- `stage-04-mapping.md`: `draft_*`, `generate_ready.json`, `mapping_log.json`, フォールバック履歴。
- `stage-05-rendering.md`: `rendering_log.json`, `audit_log.json`, `monitoring_report.json`。
- `samples/`: 代表的な JSON サンプル（`.jsonc`）。

## 運用ルール
- スキーマを変更した場合は、対応する `*.md` を更新し、必要に応じてサンプルも更新する（履歴は git ログを参照）。
- 実装（`pptx_generator/models.py`）とテスト（`tests/` 配下）を同時に調整すること。
- スキーマ追加時は stage ドキュメントからリンクし、参照先を明示する。

## 更新手順
1. 変更内容と影響範囲を洗い出す（関連工程・モジュール・テスト）。
2. 対応するスキーマファイルを修正し、サンプル JSON を更新。
3. ToDo / Roadmap に必要なタスクを登録し、関連チームへ周知する。
4. CI でスキーマ検証・テストを通し、レビュー観点をまとめる。
