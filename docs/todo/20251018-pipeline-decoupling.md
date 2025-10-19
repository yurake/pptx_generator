---
目的: `pptx gen` の工程構成を再設計し、工程5/6の疎結合化と再実行性向上の方針を固める
関連ブランチ: feat/pipeline-decoupling
関連Issue: #215
roadmap_item: RM-023 コンテンツ承認オーサリング基盤
---
- [x] ブランチ作成と初期コミット
  - メモ: feat/pipeline-decoupling を main から作成し、ToDo 追加コミット（docs(todo): track pipeline decoupling task）を作成済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 計画案を提示し、ユーザー承認メッセージ（2025-10-18 23:24「ok」）を取得済み。
- [x] 会話整理ノート作成タスクの追加
  - メモ: ToDo に「会話整理ノート作成」タスクを追加済み。実際のノート作成は後工程で実施予定。
- [x] 設計・実装方針の確定
  - メモ: 設計メモを `docs/notes/20251018-pipeline-decoupling-design.md` にまとめ、工程5/6分割とデータ変換方針を決定済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/stage-05-mapping.md` / `stage-06-rendering.md` と `docs/design` 配下のスキーマ・ステージ資料を更新済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `pptx mapping` / `pptx render` コマンド追加、`rendering_ready_to_jobspec` 実装、`RenderingReadyMeta` 拡張を完了。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest` を実行し 119 件成功。併せて `uv run pptx mapping ...` と `uv run pptx render ...` で新コマンドの出力を確認。
- [x] ドキュメント更新
  - メモ: README へ新コマンドを追記し、roadmap/runbook は影響なしと判断済み。
  - [x] docs/roadmap 配下（影響なしのため更新不要と確認）
  - [x] docs/requirements 配下（整合確認済み）
  - [x] docs/design 配下（整合確認済み）
  - [x] docs/runbook 配下（影響なしのため更新不要と確認）
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue #215 を関連付け済み。
- [x] PR 作成
  - メモ: PR #217 https://github.com/yurake/pptx_generator/pull/217（2025-10-19 完了）
## メモ
-
- [ ] 次タスク: RM-033 パイプライン工程3/4独立化準備
  - メモ: 工程3/4独立CLI化の調査とテスト観点整理を RM-033 に集約。設計・実装検討は当該 ToDo で行う。
