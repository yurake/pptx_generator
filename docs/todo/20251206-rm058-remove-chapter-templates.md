---
目的: RM-058 章テンプレート機能の撤廃
関連ブランチ: feat/rm058-prepare-policy-internalization
関連Issue: #387
roadmap_item: RM-058 プレペア骨子内製化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ `feat/rm058-prepare-policy-internalization` を継続利用。追加コミットで章テンプレ削除対応を反映予定。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: 章テンプレート資産 (`config/chapter_templates/`)、CLI `outline`/`compose` のテンプレ関連オプション、Draft structuring / layout 評価のテンプレ依存ロジック、関連テスト・ドキュメントを削除または更新する。
    - ドキュメント／コード修正方針: CLI オプションとハンドラロジックを撤廃し、テンプレ適合率に依存するメタ項目を整備し直す。対応する単体テスト・統合テストを更新し、ドキュメントの記述も改訂する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo に進捗を記録し、作業完了後にドラフト PR でまとめて共有する。
    - 想定影響ファイル: `config/chapter_templates/**/*`, `src/pptx_generator/cli_commands/outline.py`, `compose.py`, `cli_handlers/outline.py`, `compose.py`, `draft_intel.py`, draft structuring系 (`pipeline/draft_structuring/*`), テスト群, 関連 docs。
    - リスク: 章テンプレ基盤を利用しているワークフローがあれば後方互換がなくなる。`layout_score_detail` などテンプレ由来のログ項目の整理漏れに注意。
    - テスト方針: `uv run --extra dev pytest` 全体実行。特に `tests/cli/test_cli_outline_generation.py` など章テンプレ依存テストの更新確認。
    - ロールバック方法: 章テンプレ削除コミットを revert し、`config/chapter_templates` と CLI オプションを復旧する。
    - 承認メッセージ ID／リンク: ユーザー返信「ok」
- [x] 設計・実装方針の確定
  - メモ: 
    - CLI は章テンプレ関連のオプションを提供せず、outline / compose では intent 情報だけで章構成を整理する。
    - Draft structuring・mapping は intent / usage_tags のスコアリングへ統一し、テンプレ互換の採点メタは保持しない。
    - 監査系メタデータは章テンプレ ID を記録せず intent を軸に整理する。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: 章テンプレ CLI オプション・テンプレ依存ロジックを削除し、`config/chapter_templates/` を廃止。Draft structuring のテンプレ評価を無効化。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実行（330 passed, 1 skipped）。差分確認のため `uv run --extra dev diff-cover coverage.xml --compare-branch origin/feat/rm058-prepare-policy-internalization` で 100% を確認。
- [x] ドキュメント更新
  - メモ: 章テンプレ関連記述を最新仕様へ更新（cli/design/requirements ノート等）、`docs/AGENTS.md` を整理。
  - [x] docs/roadmap 配下
    - メモ: 章テンプレに関する追加変更は不要（既存ロードマップ項目は RM-058 にて更新済み）。
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
    - メモ: 章テンプレ参照のある runbook なし（更新不要）。
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] リリースノート更新
  - メモ: 章テンプレ廃止で発生する CLI 互換性変更と運用上の通知事項を RM-058 のリリースノートへ整理する。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [x] PR 作成
  - メモ: PR #388 https://github.com/yurake/pptx_generator/pull/388（2025-12-06 完了）

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
