---
目的: `pptx template` コマンドで実スライドの図形・段落情報を取得できるようにする
関連ブランチ: feat/rm061-usage-tags-governance
関連Issue: #289
roadmap_item: RM-061 usage_tags ガバナンス強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm061-usage-tags-governance` を継続利用
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を反映
    - 対象整理（スコープ、対象ファイル、前提）: `pptx template` コマンドに `--slide` オプションを追加し、テンプレート抽出時に実スライド（`Presentation.slides`）の情報だけを JSON 出力する。既存テンプレ仕様の取得は不要。
    - ドキュメント／コード修正方針: CLI・ヘルパーにフラグを渡し、`SlideSnapshot` 等を流用してスライド情報を `.pptx/extract/slide_snapshot.json`（仮）へ保存。出力先は既定の `--output` を利用。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新と PR で共有。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/pipeline/template_extractor.py`, `tests/test_cli_integration.py`。
    - リスク: スライド数が多いテンプレで JSON が肥大化する程度。後方互換は考慮しない。
    - テスト方針: `pytest tests/test_cli_integration.py`。`--slide` 指定時にスナップショットが生成され、段落テキストが記録されることを確認。
    - ロールバック方法: `--slide` オプションと関連コードを削除。
    - 承認メッセージ ID／リンク: 現メッセージ
- [x] 設計・実装方針の確定
  - メモ: `pptx template --slide` でスライド情報を抽出する構成を Plan 承認時に確定済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: JSON 出力の追加のみで既存要件に変更がないため追加ドキュメントは不要。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `--slide` オプション追加と slide_snapshot.json 出力ロジックを実装。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_integration.py`
- [x] ドキュメント更新
  - メモ: README と notes でスライド抽出手順を確認し追加更新不要と判断。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [x] PR 作成
  - メモ: PR #290 にて対応済み。

## メモ
- 計画のみで完了する場合は、判断者・判断日と次アクション条件をここに記載する。
