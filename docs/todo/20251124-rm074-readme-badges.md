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
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-11-26 Plan（本スレッドメッセージ）承認済み。`.coveragerc` を廃止し、`pyproject.toml` の `[tool.coverage.*]` と `pytest addopts` で `uv run --extra dev pytest` 実行時に自動で `coverage.xml` を生成する方針。影響ファイルは `pyproject.toml` と必要なドキュメントのみ。
- [x] 設計・実装方針の確定
  - メモ: coverage 設定を `pyproject.toml` へ集約し、CI でも同一コマンドで動作させる。追加のスクリプトや post-processing は実施しない。
- [x] 設計・実装方針メモの共有
  - メモ: `docs/notes/README-badges-plan.md` に coverage 設定統一のメモを追記。
- [x] ドキュメント更新（要件・設計）
  - メモ: 今回の対応は運用メモのみ更新で足りるため、要件・設計文書は変更不要と判断（理由を記録済み）。
  - [x] docs/requirements 配下
    - メモ: coverage 設定変更による要件差分なし。
  - [x] docs/design 配下
    - メモ: 実装構成に影響せず、追加記載不要。
- [x] 実装
  - メモ: `pyproject.toml` に `pytest-cov` を dev 依存へ追加し、`[tool.coverage.*]` と `addopts` を設定。`.coveragerc` は削除済み。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実行し、`coverage.xml` に `<source>src</source>` と `pptx_generator/...` パスが出力されることを確認。
- [x] ドキュメント更新（カテゴリ確認）
  - メモ: `docs/notes/README-badges-plan.md` に coverage 設定統一を追記。その他カテゴリは影響なし。
  - [x] docs/roadmap 配下
    - メモ: 変更なし。
  - [x] docs/requirements 配下
    - メモ: 変更なし。
  - [x] docs/design 配下
    - メモ: 変更なし。
  - [x] docs/runbook 配下
    - メモ: 変更なし。
  - [x] README.md / AGENTS.md
    - メモ: 変更なし。
- [ ] 関連Issue 行の更新
  - メモ: 必要な場合に更新。
- [ ] チェックリスト整合確認
  - メモ: 工程完了時に整合を確認。
- [ ] PR 作成
  - メモ: 修正完了後に PR を作成し、Plan 承認メッセージ ID を記載。

## メモ
- SonarCloud で coverage.xml のパス解決に失敗しているため、coverage レポートの source path 設定を修正する。
