---
目的: RM-074 README バッジ整備と静的解析導入
関連ブランチ: fix/rm074-sonar-coverage
関連Issue: #306
roadmap_item: RM-074 README バッジ整備と静的解析導入
---

## 第1フェーズ（2025-11-24 完了ログ）

- [x] ブランチ作成・初期コミット・push
  - メモ: main から docs/rm074-readme-badges を作成し、commit 1fa52d6 (docs(rm074): add todo for README badges) を push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-11-24 Plan 承認済み（ユーザーメッセージ:「ok」）。README バッジ追加、CI SonarCloud 連携、関連ドキュメント整備が対象。
- [x] 設計・実装方針の確定
  - メモ: SonarCloud 連携とバッジ構成を確定。
- [x] 設計・実装方針メモの共有
  - メモ: `docs/notes/README-badges-plan.md` に詳細を記録。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/notes/README-badges-plan.md`, `docs/requirements/requirements.md` を更新。
- [x] 実装
  - メモ: `sonar-project.properties`, `.github/workflows/ci.yml`, `README.md` などを更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev --with pytest-cov pytest --cov=src --cov-report=xml` と `dotnet run --project dotnet/Polisher.Tests` を実行。
- [x] ドキュメント更新（各カテゴリ確認）
  - メモ: 必要カテゴリを再確認し変更なしの箇所はメモ済み。
- [x] 関連Issue 行の更新
  - メモ: #306 を参照。
- [x] チェックリスト整合確認
  - メモ: 2025-11-24 時点で整合。
- [x] PR 作成
  - メモ: PR #307 (ci: SonarCloud 連携と README バッジ整備) を提出。

## 2025-11-26 再開タスク（SonarCloud カバレッジ取り込み修正）

- [x] ブランチ作成・初期コミット・push
  - メモ: main から fix/rm074-sonar-coverage を作成し、本 ToDo 再オープン差分を初期コミット（docs(rm074): reopen todo for sonar coverage）として push 済み。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: coverage.xml のパス不整合で SonarCloud がカバレッジを取り込めない不具合への対処。Plan 承認待ち。
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認後に記載。
- [ ] 設計・実装方針メモの共有
  - メモ: 必要に応じて `docs/notes/README-badges-plan.md` へ追記。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 影響範囲を確認し、必要な場合に更新。不要なら理由を記載。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: coverage パス設定／CI 変更を予定。
- [ ] テスト・検証
  - メモ: `uv run --extra dev --with pytest-cov pytest --cov=src --cov-report=xml`、必要に応じて追加検証を実施。
- [ ] ドキュメント更新（カテゴリ確認）
  - メモ: 影響箇所を確認後に記載。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 必要な場合に更新。
- [ ] チェックリスト整合確認
  - メモ: 工程完了時に整合を確認。
- [ ] PR 作成
  - メモ: 修正完了後に PR を作成し、Plan 承認メッセージ ID を記載。

## メモ
- SonarCloud で coverage.xml のパス解決に失敗しているため、coverage レポートの source path 設定を修正する。
