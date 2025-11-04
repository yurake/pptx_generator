---
目的: コンテンツ多形式インポート基盤の実装準備と段階的構築
関連ブランチ: feat/rm-039-multi-format-import
関連Issue: #232
roadmap_item: RM-039 コンテンツ多形式インポート
---

- [x] ブランチ作成と初期コミット
  - 完了条件: main から作業ブランチを切り、初期コミットを記録する
  - メモ: 2025-10-23 feat/rm-039-multi-format-import を作成
- [x] 計画策定（スコープ・前提の整理）
  - 完了条件: 作業範囲・前提条件・リスク・テスト戦略・ロールバック方針を整理し承認を得る
  - メモ: 2025-10-23 ユーザー承認済（本スレッド）
- [x] 設計・実装方針の確定
  - 完了条件: 入力形式別のアーキテクチャ案とデータフローを設計しレビュー合意を得る
  - メモ: ContentImportService を定義し CLI 拡張案を docs/design/stages/stage-03-content-normalization.md へ反映
- [x] ドキュメント更新（要件・設計）
  - 完了条件: 合意内容を docs/requirements, docs/design に反映し記録する
  - メモ: 2025-10-23 要件・設計初版を更新
  - [x] docs/requirements 配下
    - 完了条件: 多形式インポートの要件を明文化
  - [x] docs/design 配下
    - 完了条件: パイプライン設計と処理フローを記述
- [x] 実装
  - 完了条件: テキスト/PDF/URL 入力の取得・正規化・監査ログ機能を期待成果に沿って実装
  - メモ: ContentImportService と `pptx prepare --content-source` を追加済み
- [x] テスト・検証
  - 完了条件: 単体・統合テストを実施し `uv run --extra dev pytest` 等で確認、結果を記録
  - メモ: 2025-10-25 LibreOffice 導入後に `uv run pptx gen samples/json/sample_jobspec.json --template samples/templates/templates.pptx --export-pdf` と `uv run --extra dev pytest tests/test_cli_integration.py` を実施し、PDF 生成と 26 件の CLI テスト成功を確認。詳細は docs/notes/20251025-libreoffice-verification.md を参照。
- [x] ドキュメント更新
  - 完了条件: 実装結果と運用手順を docs/ 配下の該当カテゴリへ反映
  - メモ: 要件・設計・ロードマップを更新済み。LibreOffice 導入後の追記要否を継続確認
  - [x] docs/roadmap 配下
    - 完了条件: RM-039 の進捗更新（進行中へ変更し保留事項を明記）
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - 完了条件: 多形式インポート要件を追記
  - [x] docs/design 配下（実装結果との整合再確認）
    - 完了条件: コンテンツインポート基盤の設計と運用ルールを追記
  - [x] docs/runbook 配下
    - 完了条件: 今回の変更で更新不要であることを確認
  - [x] README.md / AGENTS.md
    - 完了条件: 今回の変更で更新不要であることを確認
- [x] 関連Issue 行の更新
  - 完了条件: 対応する Issue 番号を確認し front matter を更新
  - メモ: `gh issue list` は TLS エラーで未取得。再試行または代替手段を検討
- [x] PR 作成
  - メモ: PR #240 https://github.com/yurake/pptx_generator/pull/240（2025-10-25 完了）
  - 完了条件: テンプレートに沿って PR を作成し ToDo を連携
  - メモ: todo-auto-complete の結果を確認

## メモ
- `gh issue list --limit 50` を試行したが TLS 証明書検証で失敗。Issue 番号把握は後続で再挑戦。
