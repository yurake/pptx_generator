---
目的: CLI 生成結果の検証を自動化し、手動確認を効率化する
担当者: Codex
関連ブランチ: main
期限: 2025-10-12
関連Issue: #92
関連PR: 未設定
closed_at: 2025-10-05
---

- [x] 要件整理と検証観点の整理
  - メモ: 2025-10-05 CLI 実行フローと検証観点を整理
- [x] pytest に CLI 統合テストを追加
  - メモ: 2025-10-05 `tests/test_cli_integration.py` を実装し `--workdir` / `--template` をカバー
- [x] CI / ドキュメントを更新
  - メモ: 2025-10-05 pytest 実行で CLI 検証を自動化し、README/CONTRIBUTING の手順を更新

## メモ
- 余白やフォントなど高度な検証は別途タスクで扱う。
- 2025-10-05 CLI 検証は pytest の統合テストへ統合し、CI では `uv run --extra dev pytest` のみを実行。

<!-- BEGIN: issues-sync -->
## Synced Issues
- [x] 要件整理と検証観点の整理 (#90)
- [x] pytest に CLI 統合テストを追加 (#91)
- [x] CI / ドキュメントを更新 (#92)
<!-- END: issues-sync -->
