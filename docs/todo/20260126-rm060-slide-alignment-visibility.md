---
目的: RM-060 Stage3 ID 整合性強制の運用改善（整合結果の可視化とUATでの検証性向上）
関連ブランチ: feat/rm060-slide-alignment-visibility
関連Issue: 未作成
roadmap_item: RM-060 Stage3 ID 整合性強制
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-26: feat/rm060-slide-alignment-visibility を作成。初期コミット=6769464（ToDo起票）。push未実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: RM-060 の可視化対応。SlideIdAligner の結果を generate_ready_meta.json に出力し、CLI/API から整合設定を調整可能にする。対象: cli_commands/utils.py, cli_commands/compose.py, cli_commands/outline.py, cli_handlers/compose.py, cli_handlers/outline.py, api/stages.py, pipeline/draft_structuring/{dynamic_runtime.py, generate_ready_runtime.py}, docs/design/cli/cli-command-reference.md。
    - ドキュメント／コード修正方針: CLI に slide-alignment オプション追加、DraftStructuringOptions へ伝播。dynamic_runtime で alignment meta/records を artifacts に保存し、generate_ready_meta へ同梱。CLI リファレンス更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo に実装・判断を随時記録。レビューで generate_ready_meta 出力を確認。
    - 想定影響ファイル: 生成物（generate_ready_meta.json）構造、compose/outline CLI オプション、API compose payload。
    - リスク: alignment オプション未指定時の既定値不整合、meta 生成サイズ増。既定値は DraftStructuringOptions と整合させる。
    - テスト方針: 既存の compose/outline 実行で generate_ready_meta に slide_alignment が含まれることを手動確認（必要ならサンプル spec で再現）。
    - ロールバック方法: 追加オプションと payload 追加を戻し、generate_ready_meta から slide_alignment を削除。
    - 承認メッセージ ID／リンク: 2026-01-26 ユーザー承認「OK」
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: CLI/API へ slide alignment オプションを追加し、dynamic runtime で alignment meta/records を generate_ready_meta に同梱。CLI リファレンス更新済み。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト: 実施
      - `UV_CACHE_DIR=.pptx/uv-cache uv run --extra dev pytest tests/pipeline/compose/test_draft_structuring_step.py tests/layout_validation/test_slide_alignment_metrics.py`
        - 結果: 23 passed
    - ユーザー経路の手動確認（必要な場合）: 実施（aws-claude）
      - Stage2 Prepare: `PPTX_LLM_PROVIDER=aws-claude PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli prepare samples/input/bullet_only.md --mode dynamic --output .pptx/uat-rm060/prepare-live`
        - 出力: `.pptx/uat-rm060/prepare-live/prepare_card.json` ほか生成
      - Stage3 Outline: `PPTX_LLM_PROVIDER=aws-claude PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli outline samples/extract/jobspec.json --prepare-cards .pptx/uat-rm060/prepare-live/prepare_card.json --output .pptx/uat-rm060/outline-live`
      - Stage3 Compose: `PPTX_LLM_PROVIDER=aws-claude PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli compose samples/extract/jobspec.json --prepare-cards .pptx/uat-rm060/prepare-live/prepare_card.json --output .pptx/uat-rm060/compose-live`
      - Stage4 Gen: `PPTX_LLM_PROVIDER=aws-claude PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli gen .pptx/uat-rm060/compose-live/generate_ready.json --output .pptx/uat-rm060/gen-live`
        - 警告: Rendering warnings 39 / Monitoring alerts 15（サンプルコンテンツ由来）
    - 生成物の確認があれば、その方法と結果: outline-live / compose-live の `generate_ready_meta.json` で `slide_alignment` を確認（records 16件）
    - 静的UAT（aws-claude / static small jobspec）:
      - Stage2 Prepare: `PPTX_LLM_PROVIDER=aws-claude PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli prepare samples/input/bullet_only.md --mode static --jobspec .pptx/uat-rm060/template-static-small/jobspec.json --output .pptx/uat-rm060/prepare-static`
      - Stage3 Compose: `PPTX_LLM_PROVIDER=aws-claude PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli compose .pptx/uat-rm060/template-static-small/jobspec.json --prepare-cards .pptx/uat-rm060/prepare-static/prepare_card.json --output .pptx/uat-rm060/compose-static`
      - Stage4 Gen: `PPTX_LLM_PROVIDER=aws-claude PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli gen .pptx/uat-rm060/compose-static/generate_ready.json --output .pptx/uat-rm060/gen-static`
        - 警告: Rendering warnings 1 / Monitoring alerts 1（empty_placeholder: Content Placeholder 2 / slide_id=one_column_detail-01）
      - 確認: compose-static の `generate_ready_meta.json` に `slide_alignment` は出力されない
- [x] ドキュメント更新
  - メモ: CLI リファレンス（docs/design/cli/cli-command-reference.md）へ slide alignment オプションを追記済み。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（変更不要: ロードマップ項目の変更なし）
  - [x] docs/requirements 配下（変更不要: 仕様変更なし）
  - [x] docs/design 配下（更新済み: CLI コマンドリファレンス）
  - [x] docs/runbook 配下（変更不要: 運用手順の変更なし）
  - [x] README.md / AGENTS.md（変更不要: 追加手順なし）
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [x] PR 作成
  - メモ: PR #2 https://github.com/kkeito-investigate/pptx_generator/pull/2

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: RM-060 は SlideIdAligner の可視化が主目的。main とは別 worktree で作業中。
  - 決定と理由: generate_ready_meta に slide_alignment を追加し、CLI/API で調整可能にする方針。
  - リスク(UNCONFIRMED): meta 出力が増えることで下流ツールが未対応の可能性。
  - Now/Next: 実装・UAT（aws-claude dynamic/static）・自動テスト完了。次はPR作成。
  - テスト実績/抜け: uv pytest 23件パス。UATは aws-claude で Stage2/3/4 実施済み（dynamic: bullet_only / static: small jobspec 1枚）。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
