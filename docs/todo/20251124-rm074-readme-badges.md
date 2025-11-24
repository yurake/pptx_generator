---
目的: RM-074 README バッジ整備と静的解析導入
関連ブランチ: docs/rm074-readme-badges
関連Issue: #306
roadmap_item: RM-074 README バッジ整備と静的解析導入
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から docs/rm074-readme-badges を作成し、commit 1fa52d6 (docs(rm074): add todo for README badges) を push 済み。上位 worktree の権限制約により upstream 設定のみ手動追従が必要。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-11-24 Plan 承認済み（ユーザーメッセージ:「ok」）。以下の方針で進行。
    - 対象整理（スコープ、対象ファイル、前提）: README へのバッジ追加、`sonar-project.properties` 新設、`.github/workflows/ci.yml` 更新、`docs/notes/README-badges-plan.md`／関連ドキュメント整備。Secrets 未設定時のフォールバックは不要で、SonarCloud バッジは取得可能なメトリクスをすべて掲載する。
    - ドキュメント／コード修正方針: `sonar-project.properties` に必要キーを定義し、CI へ SonarCloud ステップを追加。README 先頭へ License / CI / Python / SonarCloud(複数) バッジを並べ、ノートと要件ドキュメントへ運用手順を追記。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 記載の各工程を完了しつつ、Plan 内容を docs/notes へ反映。PR 説明と ToDo で Plan メッセージ ID（本メモ）を参照。
    - 想定影響ファイル: `README.md`, `.github/workflows/ci.yml`, `sonar-project.properties`, `docs/notes/README-badges-plan.md`, `docs/requirements/requirements.md`（必要に応じて）。
    - リスク: SonarCloud Secrets 未設定時に CI が失敗する点（許容）。バッジ URL のプロジェクトキー相違によるリンクエラー → ノートでキー統一を明記して抑止。
    - テスト方針: `uv run --extra dev pytest`, `dotnet run --project dotnet/Polisher.Tests` をローカル実行。SonarCloud ステップは GitHub Actions 上で確認。
    - ロールバック方法: 対象ファイルの差分を個別に `git revert`。Secrets を無効化すれば SonarCloud 実行も即停止可能。
    - 承認メッセージ ID／リンク: ユーザー「ok」（2025-11-24 本スレッド）のメッセージ。
- [x] 設計・実装方針の確定
  - メモ: 2025-11-24 に上記方針を最終確定。SonarCloud 連携は `sonar-project.properties` と GitHub Actions (`SonarSource/sonarcloud-github-action@v2`) の組合せで恒久運用し、Python テストは `pytest --cov=src --cov-report=xml` へ統一する。README 先頭に License/CI/Python と SonarCloud 10 指標のバッジをセンタリング配置し、ノートと要件へ反映済み。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 詳細方針とバッジ URL 一覧を `docs/notes/README-badges-plan.md` に追記し、参照先を整備した。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/notes/README-badges-plan.md` にバッジ一覧と運用手順、`docs/requirements/requirements.md` に CI + README バッジ要件を追記済み。設計ドキュメントは今回対象外のため更新不要。サポートされない Sonar 指標（Security Hotspots など）は除外済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下（今回の変更範囲外のため更新不要）
- [x] 実装
  - メモ: `sonar-project.properties` 新設、`.github/workflows/ci.yml` にカバレッジ付き pytest と SonarCloud ステップを追加。`README.md` に License/CI/Python/Sonar バッジテーブルを挿入し、`.gitignore` にカバレッジ成果物を追加。
- [x] テスト・検証
  - メモ: `uv run --extra dev --with pytest-cov pytest --cov=src --cov-report=xml`（192件成功、coverage.xml生成）と `dotnet run --project dotnet/Polisher.Tests`（警告1件・テスト成功）をローカル実行。
- [x] ドキュメント更新
  - メモ: ロードマップ変更なし。requirements は更新済み、その他カテゴリは影響なしのため未更新。
  - [x] docs/roadmap 配下（今回の対応範囲外のため変更なし）
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（影響なし）
  - [x] docs/runbook 配下（影響なし）
  - [x] README.md / AGENTS.md（README バッジ更新済み）
- [x] 関連Issue 行の更新
  - メモ: `#306` を確認済み。今後も進捗があれば ToDo 内の記述を更新する。
- [x] チェックリスト整合確認
  - メモ: 2025-11-24 時点でチェック状態と成果物が一致することを点検。残タスクは「PR 作成」のみ。
- [ ] PR 作成
  - メモ: 未着手

## メモ
- 設計方針の確定・共有およびチェックリスト整合を反映済み。残タスクは PR 作成とレビュー対応。
