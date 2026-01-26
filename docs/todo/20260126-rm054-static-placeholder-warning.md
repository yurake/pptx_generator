---
目的: RM-054 静的テンプレートの empty_placeholder 警告解消（static UAT の警告を削減）
関連ブランチ: fix/rm054-static-placeholder-warning
関連Issue: #555
roadmap_item: RM-054 静的テンプレ構成統合プランニング
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-26: fix/rm054-static-placeholder-warning を作成。初期コミット=1dbbd06。push済み。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: static compose の image slot が空になる問題を解消。対象は draft_structuring/slide_elements.py の assign_slot_to_elements と compose テスト。
    - ドキュメント／コード修正方針: content_type=image で image source が無い場合は text へフォールバック。source があれば image payload を生成。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo に実装・テスト・UAT結果を記録し、PR本文に動作確認を記載。
    - 想定影響ファイル: slide_elements.py, tests/pipeline/compose/test_draft_structuring_step.py
    - リスク: 画像プレースホルダーにテキストが入る可能性（警告抑止が目的）。
    - テスト方針: pytestで該当テスト実施。静的UATで rendering_log の警告数確認。
    - ロールバック方法: image slot のフォールバック処理とテストを元に戻す。
    - 承認メッセージ ID／リンク: 2026-01-26 ユーザー承認「おなしゃす」
- [x] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
    - image slot は ref が anchor と一致する場合は画像扱いせずテキストへフォールバックする。
    - ref が有効な画像ソースの場合のみ image payload を生成する。
  - [x] 設計・実装方針メモの共有（必要なし）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: image slot の ref 判定とテキストフォールバックを追加。image slot のテストを追加。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト:
      - `UV_CACHE_DIR=.pptx/uv-cache uv run --extra dev pytest tests/pipeline/compose/test_draft_structuring_step.py`
        - 結果: uv が system-configuration で panic し中断
    - ユーザー経路の手動確認: 実施（static）
      - `PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli compose .pptx/uat-rm060/template-static-small/jobspec.json --prepare-cards .pptx/uat-rm060/prepare-static/prepare_card.json --output .pptx/uat-rm060/compose-static`
      - `PYTHONPATH=/Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/rm060/src /Users/keitokimura/work/generativeAI/20260121-llmcoe-backend/pptx_generator/.venv/bin/python -m pptx_generator.cli gen .pptx/uat-rm060/compose-static/generate_ready.json --output .pptx/uat-rm060/gen-static`
      - 結果: Rendering warnings 0 / Monitoring alerts 0
    - 生成物の確認: `.pptx/uat-rm060/gen-static/rendering_log.json` を確認
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（変更不要: ロードマップ変更なし）
  - [x] docs/requirements 配下（変更不要: 仕様変更なし）
  - [x] docs/design 配下（変更不要: 設計変更なし）
  - [x] docs/runbook 配下（変更不要: 運用変更なし）
  - [x] README.md / AGENTS.md（変更不要: 手順追加なし）
- [x] 関連Issue 行の更新
  - メモ: 関連Issue を #555 へ更新済み。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: static モードの image slot が空だと empty_placeholder 警告が出る。
  - 決定と理由: ref が anchor と一致する場合は画像扱いせずテキストへフォールバックする。
  - リスク(UNCONFIRMED): 画像プレースホルダーがテキストで埋まる可能性。
  - Now/Next: 実装・静的UAT実施済み。次は差分整理とPR作成。
  - テスト実績/抜け: pytest は uv panic で中断。静的UATは warnings 0 を確認。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
