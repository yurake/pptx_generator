---
目的: コンテンツ多形式インポート基盤の実装準備と段階的構築
関連ブランチ: feat/rm-039-multi-format-import
関連Issue: #232
roadmap_item: RM-039 コンテンツ多形式インポート
---

- [x] ブランチ作成と初期コミット
  - 担当: Codex / 完了条件: main から作業ブランチを切り、初期コミットを記録する
  - メモ: 2025-10-23 feat/rm-039-multi-format-import を作成
- [ ] 計画策定（スコープ・前提の整理）
  - 担当: Codex / 完了条件: 作業範囲・前提条件・リスク・テスト戦略・ロールバック方針を整理し承認を得る
  - メモ: Plan 承認待ち
- [ ] 設計・実装方針の確定
  - 担当: Codex / 完了条件: 入力形式別のアーキテクチャ案とデータフローを設計しレビュー合意を得る
  - メモ: 要件差異があれば docs/design/ へ反映
- [ ] ドキュメント更新（要件・設計）
  - 担当: Codex / 完了条件: 合意内容を docs/requirements, docs/design に反映し記録する
  - メモ: 要件調整内容を整理
  - [ ] docs/requirements 配下
    - 担当: Codex / 完了条件: 多形式インポートの要件を明文化
  - [ ] docs/design 配下
    - 担当: Codex / 完了条件: パイプライン設計と処理フローを記述
- [ ] 実装
  - 担当: Codex / 完了条件: テキスト/PDF/URL 入力の取得・正規化・監査ログ機能を期待成果に沿って実装
  - メモ: 実装対象モジュールと未対応事項を記録
- [ ] テスト・検証
  - 担当: Codex / 完了条件: 単体・統合テストを実施し `uv run --extra dev pytest` 等で確認、結果を記録
  - メモ: 出力生成やエッジケースを含めて検証
- [ ] ドキュメント更新
  - 担当: Codex / 完了条件: 実装結果と運用手順を docs/ 配下の該当カテゴリへ反映
  - メモ: 影響範囲とフォールバック手順を整理
  - [ ] docs/roadmap 配下
    - 担当: Codex / 完了条件: RM-039 の進捗更新
  - [ ] docs/requirements 配下（実装結果との整合再確認）
    - 担当: Codex / 完了条件: 要件差分を更新
  - [ ] docs/design 配下（実装結果との整合再確認）
    - 担当: Codex / 完了条件: 設計差分を反映
  - [ ] docs/runbook 配下
    - 担当: Codex / 完了条件: 運用手順を更新
  - [ ] README.md / AGENTS.md
    - 担当: Codex / 完了条件: 対応が必要な場合のみ更新
- [x] 関連Issue 行の更新
  - 担当: Codex / 完了条件: 対応する Issue 番号を確認し front matter を更新
  - メモ: `gh issue list` は TLS エラーで未取得。再試行または代替手段を検討
- [ ] PR 作成
  - 担当: Codex / 完了条件: テンプレートに沿って PR を作成し ToDo を連携
  - メモ: todo-auto-complete の結果を確認

## メモ
- `gh issue list --limit 50` を試行したが TLS 証明書検証で失敗。Issue 番号把握は後続で再挑戦。
