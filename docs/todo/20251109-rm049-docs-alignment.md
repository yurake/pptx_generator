---
目的: RM-049 のスコープ最適化内容に合わせて CLI/運用ドキュメントを最新仕様へ揃える
関連ブランチ: feat/rm049-scope-docs
関連Issue: #258
roadmap_item: RM-049 pptx gen スコープ最適化
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm049-scope-docs を main から作成済み。本 ToDo の追加を初期コミットとして登録。
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - 対象整理（スコープ、対象ファイル、前提）: `AGENTS.md`／`src/AGENTS.md`／`config/AGENTS.md`／`docs/design/cli-command-reference.md`／`docs/requirements/stages/stage-05-mapping.md` などで `pptx gen` が旧仕様（jobspec 入力や `--template` 前提）になっている箇所を最新仕様へ更新する。その他関連ドキュメントは影響調査を行い、必要な場合のみ加筆修正する。
    - ドキュメント／コード修正方針: 最新実装（`generate_ready.json` 入力・テンプレ自動解決）に沿う記述へ書き換え、使用例は `compose` → `gen` の 2 段ステップで提示する。工程5の要件ドキュメントや各種ガイドも同じ観点で整合を取る。
    - 確認・共有方法（レビュー、ToDo 更新など）: 変更ファイルをセルフレビューし、本 ToDo に進捗を記録。必要に応じて追加の差分をユーザーへ共有する。
    - 想定影響ファイル: `AGENTS.md`, `src/AGENTS.md`, `config/AGENTS.md`, `docs/design/cli-command-reference.md`, `docs/requirements/stages/stage-05-mapping.md`, 関連参照部分。
    - リスク: ドキュメント間で記述ゆれが残ると利用者が旧コマンドを参照してしまう恐れ。修正範囲が広がる場合は再度承認を得る。
    - テスト方針: 文章ベースで CLI 手順を読み合わせ、必要に応じてサンプルコマンドを実行して確認。
    - ロールバック方法: 対象ファイルの変更を 1 つのコミットにまとめ、問題が発生した場合は当該コミットを revert する。
    - 承認メッセージ ID／リンク: ユーザーからの「承認します。」メッセージ（本スレッド）。
- [x] 設計・実装方針の確定
  - メモ: CLI ドキュメントは `generate_ready.json` を唯一の入力とする前提で統一し、`compose` → `gen` の 2 段フローを共通指針として採用。
- [x] ドキュメント更新（要件・設計）
  - メモ: stage-05 要件と CLI 設計ガイドを現行仕様へ更新済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `AGENTS.md` / `src/AGENTS.md` / `config/AGENTS.md` の記述を更新し、CLI 設計ガイド・要件ドキュメントと整合させた。
- [x] テスト・検証
  - メモ: 変更箇所をセルフレビューし、CLI 手順が実装と矛盾しないことを確認（実行テストは未実施）。
- [x] ドキュメント更新
  - メモ: 影響を確認した結果、README・runbook・roadmap への追加更新は不要。AGENTS 系と設計／要件ドキュメントを更新済み。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue #258 の進捗に応じて更新予定。
- [ ] PR 作成
  - メモ:

## メモ
