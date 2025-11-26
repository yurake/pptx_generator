---
目的: RM-066 テンプレ指定統一 CLI整備
関連ブランチ: feat/rm066-template-option-consolidation
関連Issue: #323
roadmap_item: RM-066 テンプレ指定統一 CLI整備
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: ブランチを作成（feat/rm066-template-option-consolidation）。初期コミット `docs(rm066): add todo skeleton` を実施済み。リモート push は未実施。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: CLI (`pptx compose` / `pptx mapping`) が既に jobspec.meta.template_path を必須とする現状を確認し、ドキュメント一式から旧 `--template` 指定手順を排除してメタ依存に統一する。関連ノートでの過去手順は文脈を保ちながら必要に応じ注記追加。
    - ドキュメント／コード修正方針: コード変更は不要想定。`AGENTS.md` / `src/AGENTS.md` / `config/AGENTS.md` / `README.md` / `CONTRIBUTING.md` / `docs/policies/config-and-templates.md` などで `pptx compose` / `pptx mapping` における `--template` 指定例を削除し、jobspec.meta.template_path 参照を強調。旧手順を残す履歴ドキュメントは整合するよう注記。
    - 確認・共有方法（レビュー、ToDo 更新など）: 作業後に本 ToDo を更新し、PR 説明へリンク。必要に応じ `docs/notes/20251110-template-option-consolidation.md` へ差分メモを追記。
    - 想定影響ファイル: AGENTS 系 3 ファイル、`README.md`、`CONTRIBUTING.md`、`docs/policies/config-and-templates.md`、該当するノート類。
    - リスク: ドキュメントに旧手順が残存すると運用誤りが生じる。履歴ドキュメントを誤って改変して事実経緯が失われる可能性。
    - テスト方針: 文書更新主体のため、整合確認として `uv run --extra dev pytest tests/test_cli_integration.py` を実行して CLI フローの正常動作を確認。
    - ロールバック方法: 差分コミットを `git revert` するかブランチごと破棄。
    - 承認メッセージ ID／リンク: ユーザー承認（2025-11-26: "ok"）
- [ ] 設計・実装方針の確定
  - メモ: 
- [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 
- [x] テスト・検証
  - メモ: 2025-11-26 `uv run --extra dev pytest tests/test_cli_integration.py`（19 件成功）。
- [ ] ドキュメント更新
  - メモ: AGENTS ガイド（`AGENTS.md` / `src/AGENTS.md` / `config/AGENTS.md`）と運用ドキュメント（`docs/runbooks/pptx-analyzer.md`、`docs/qa/pdf-export-rehearsal.md`、`docs/policies/config-and-templates.md`、`docs/notes/20251105-jobspec-scaffold-validation.md`、`docs/todo/archive/20251108-rm059-jobspec-scaffold.md`）を jobspec.meta ベースへ更新済み。README / roadmap 等は現行記述で整合するため変更なし。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
