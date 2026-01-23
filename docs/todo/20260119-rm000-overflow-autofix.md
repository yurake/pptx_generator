---
目標: テキスト溢れ時に LLM で本文を枠内へ収める
関連ブランチ: verify/overflow-autofix
関連Issue: #542
roadmap_item: RM-000 例: RMなしIssue C
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名: feat/overflow-autofix / 初期コミット: docs(todo): add rm000 overflow autofix / push: 済み
    - 必ず main からブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること
    - 対象スコープ: MappingStep で body 超過時に自動短縮し末尾に "..." を付与
    - 対象ファイル: src/pptx_generator/pipeline/mapping/processor.py, tests/pipeline/mapping/test_mapping_step_layout_assignment.py
    - 前提: max_lines は layout の text_hint を使用
    - ドキュメント／コード修正方針: body を短縮し warnings に記録
    - 確認・共有方法: ToDo 更新、Issue コメント
    - 想定影響ファイル: generate_ready.json の body 出力
    - リスク: 内容の末尾が削られる
    - テスト方針: PYTHONPATH=src python -m pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py
    - ロールバック方針: 追加処理を revert
    - 承認メッセージ ID／リンク: ユーザー OK
- [x] 設計・実装方針の確定
  - メモ: max_lines 超過時に body を短縮し、末尾行へ "..." を付与する
  - [x] 設計・実装方針メモの共有（不要）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: src/pptx_generator/pipeline/mapping/processor.py, tests/pipeline/mapping/test_mapping_step_layout_assignment.py
- [x] テスト・検証
  - メモ: PYTHONPATH=src python -m pytest -n 0 tests/pipeline/mapping/test_mapping_step_layout_assignment.py / 10 passed / coverage.xml / diff-cover: python -m diff_cover.diff_cover_tool coverage.xml --compare-branch origin/main / Coverage 100%（26 lines）
- [x] ドキュメント更新
  - メモ: docs/todo/20260119-rm000-overflow-autofix.md, C:\PPT_test_textyabai\実施事項概要.md
  - メモ: 対象外: docs/roadmap 配下, docs/requirements 配下, docs/design 配下, docs/runbook 配下, README.md / AGENTS.md
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合を確認）
  - [x] docs/design 配下（実装結果との整合を確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行動更新
  - メモ: 関連Issue: #542
- [x] チェックリスト整合確認
  - メモ: 親タスクと子タスクのチェックを整合
- [x] PR 作成
  - メモ: PR #543 https://github.com/yurake/pptx_generator/pull/543

## 追加対応: LLM による自動調整

- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること
    - 対象スコープ: MappingStep で text_hint の max_lines / max_chars を超過した本文を LLM で再編集し、制約内に収める
    - 対象ファイル: src/pptx_generator/pipeline/mapping/processor.py, src/pptx_generator/pipeline/mapping/llm_fit.py, src/pptx_generator/pipeline/mapping/__init__.py, tests/pipeline/mapping/test_mapping_step_layout_assignment.py
    - 前提: LLM 返却は JSON のみ、失敗時は元本文を維持し warnings/capacity_warnings を残す
    - ドキュメント／コード修正方針: MappingStep 内で LLM 補正を実行し、`MappingAIPatch` で差分を記録
    - 確認・共有方法: ToDo 更新、Issue/PR の UAT 結果追記
    - 想定影響ファイル: generate_ready.json の body/subtitle/note 出力
    - リスク: LLM で要約され内容が変質する可能性
    - テスト方針: uv run --extra dev pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py -n 0
    - ロールバック方針: 追加した LLM 補正処理を revert
    - 承認メッセージ ID／リンク: ユーザー OK
- [x] 設計・実装方針の確定
  - メモ: overflow 検知後に LLM 補正を呼び出し、成功時のみ本文差し替えと MappingAIPatch 記録、失敗時は warnings のみ残す。LLM は mapping/llm_fit.py に集約し、MappingStep でクライアント生成→MappingSlideProcessor へ注入する。
  - [x] 設計・実装方針メモの共有
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: mapping/llm_fit.py 追加、MappingSlideProcessor へ LLM 補正追加、MappingStep でクライアント生成
- [x] テスト・検証
  - メモ: PYTHONPATH=src .venv/bin/pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py -n 0（12 passed）
  - メモ: UAT= PPTX_LLM_PROVIDER=mock .venv/bin/pptx compose samples/extract/jobspec.json --prepare-cards /tmp/prepare_card_overflow_llm.json --output /tmp/pptx_generator-uat-llm-fit-20260123-134233
  - メモ: diff-cover= .venv/bin/python -m diff_cover.diff_cover_tool coverage.xml --compare-branch origin/main（Coverage 26% / Total 580 lines / Missing 427 lines）
- [x] ドキュメント更新
  - メモ: docs/design/schema/stage-03-mapping.md を更新。Issue / PR に UAT 結果を追記
- [x] 関連Issue 行動更新
  - メモ: 関連Issue: #542（コメント https://github.com/yurake/pptx_generator/issues/542#issuecomment-3788542508）
- [ ] チェックリスト整合確認
  - メモ: 親タスクと子タスクのチェックを整合
- [x] PR 更新
  - メモ: PR #543 を更新

## メモ
- 連続性メモ（短文で上書き）
  - 前提/制約: text_hint の max_lines / max_chars に収める
  - 決定と根拠: overflow 時は LLM に再編集を依頼し、成功時のみ本文を差し替える
  - リスク(UNCONFIRMED): LLM の要約で内容が変質する可能性
  - Now/Next: Now=レビュー待ち / Next=マージ対応
  - テスト実績/抜け: PYTHONPATH=src .venv/bin/pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py -n 0（12 passed）
- 計画のみで完了する場合は、判断者・判断日・次アクション条件を記載する
