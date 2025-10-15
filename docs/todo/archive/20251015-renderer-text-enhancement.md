---
目的: レンダラーのテキスト系要素を再検証し、ギャップを洗い出して改修する
関連ブランチ: feat/renderer-text-enhance
関連Issue: #171
roadmap_item: RM-012 レンダラーテキスト強化
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/renderer-text-enhance を作成し、初期空コミットで開始点を記録
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: subtitle/notes/textboxes 要件と既存実装の差分を整理
- [x] 設計・実装方針の確定
  - メモ: ギャップ調査結果を踏まえ、必要な改修範囲とテスト対象を明文化
- [x] ドキュメント更新（要件・設計のドラフト）
  - メモ: docs/notes/20251011-renderer-text-enhancement-impl.md を補足し、検討事項を追記
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: レンダラー改修と関連ユーティリティの更新、例外処理の強化内容を記録
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_renderer.py` と `uv run --extra dev pytest tests/test_cli_integration.py` を実行し、アンカー名継承・ノートフォント・CLI 全体の回帰を確認
- [x] ドキュメント更新（結果整理）
  - メモ: 実装結果・影響範囲・確認事項を最新化
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（今回追加なし、整合確認のみ）
  - [x] docs/design 配下（今回追加なし、整合確認のみ）
  - [x] docs/runbooks 配下（変更不要を確認）
  - [x] README.md / AGENTS.md（影響なしを確認）
- [x] 関連Issueの更新
  - メモ: #171 へ進捗コメントを手動で追記し、CLI 投稿不可の旨を共有済み
- [x] PR 作成
  - メモ: PR #184 https://github.com/yurake/pptx_generator/pull/184（2025-10-15 完了）

## メモ
- RM-007 のアンカー仕様やテンプレート命名規約と矛盾がないか都度確認する。
