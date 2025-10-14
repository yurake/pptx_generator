# スキーマ変更履歴

## 2025-10-11
- 工程 3〜6 の中間 JSON を整理 (`content_approved`, `draft_approved`, `rendering_ready`, `mapping_log`, `rendering_log`, `audit_log`)。
- `ai_review.autofix_proposals.patch` を JSON Patch 形式へ統一。
- `layout_candidates` に `score` を追加し、フォールバック履歴をリスト形式へ変更。
- `rendering_log` / `audit_log` に警告コードと承認ログハッシュを追加。

## 2025-10-12
- スキーマドキュメントをステージ別ファイル（stage-01〜06）へリネームし、テンプレ受け渡しスキーマを追加。
- スキーマ参照リンクを `docs/design/stages/*` から更新し、サンプル JSON を整理。

## 2025-10-05
- 入力仕様を拡張し、テーブル (`slides[].tables`) とチャート (`slides[].charts`) を追加。
- カラーフィールドのフォーマットを `FontSpec` に揃え、サンプル JSON を更新。
