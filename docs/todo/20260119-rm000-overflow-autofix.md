---
rm: RM-000
title: "コンテンツオーバーフロー自動修正"
status: 実装完了
priority: high
created: 2026-01-19
updated: 2026-01-23
related_issues:
  - https://github.com/yurake/pptx_generator/issues/542
related_prs:
  - https://github.com/yurake/pptx_generator/pull/543
assignee: Cline
---

# コンテンツオーバーフロー自動修正

## 概要
MappingStep で text_hint (max_lines/max_chars) を超過した本文を LLM で自動調整し、枠内に収める機能を実装。

## タスク

- [x] 要件定義
  - メモ: LLM により本文・サブタイトル・ノートを max_lines/max_chars 内に収める
  - メモ: 成功時は ai_patch 記録＋要素更新、失敗時は元内容維持＋warning 記録
- [x] 設計
  - メモ: llm_fit.py に LLM クライアント追加（OpenAI/Azure/Anthropic/AWS Claude/Mock対応）
  - メモ: processor.py で capacity_controls 実行時に LLM fit を呼び出し
  - メモ: types.py に MappingTextFitRequest/Response を追加
- [x] 実装
  - メモ: src/pptx_generator/pipeline/mapping/llm_fit.py 新規作成
  - メモ: src/pptx_generator/pipeline/mapping/processor.py 修正
  - メモ: src/pptx_generator/pipeline/mapping/step.py 修正
  - メモ: src/pptx_generator/pipeline/mapping/types.py 修正
- [x] テスト・検証
  - メモ: PYTHONPATH=src .venv/bin/pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py tests/pipeline/mapping/test_llm_fit_client.py -n 0（27 passed）
  - メモ: diff-cover= .venv/bin/python -m diff_cover.diff_cover_tool coverage.xml --compare-branch upstream/main（Coverage 86% / Total 330 lines / Missing 46 lines）
  - メモ: UAT（mock LLM）= PPTX_LLM_PROVIDER=mock .venv/bin/pptx compose samples/extract/jobspec.json --prepare-cards /tmp/prepare_card_overflow_llm.json
  - メモ: UAT（aws-claude 全ステージ）= Stage1-5 実行完了、ai_patch_count=9、全スライドで LLM オーバーフロー修正動作確認済み
    - Stage1 template: 成功（warnings=0, errors=0）
    - Stage2 prepare: 成功（aws-claude, 22.8秒）
    - Stage3 compose: 成功（ai_patch=9, mapping_time=12.5秒）
    - Stage4 gen: 成功（warnings=5, alerts=5）
    - Stage5 edit: 成功（適用件数=0）
  - メモ: mapping_log.json 確認：9スライドで LLM が本文を max_lines 内に要約（例: 4行→1行、5行→2行）
- [x] ドキュメント更新
  - メモ: docs/design/schema/stage-03-mapping.md を更新。Issue / PR に UAT 結果を追記
- [x] 関連Issue 行動更新
  - メモ: 関連Issue: #542（コメント https://github.com/yurake/pptx_generator/issues/542#issuecomment-3788542508）
- [x] チェックリスト整合確認
  - メモ: 親タスクと子タスクのチェックを整合
- [x] PR 更新
  - メモ: PR #543 を更新
  - リスク(UNCONFIRMED): LLM の要約で内容が変質する可能性
  - Now/Next: Now=レビュー待ち / Next=マージ対応
  - テスト実績/抜け: PYTHONPATH=src .venv/bin/pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py tests/pipeline/mapping/test_llm_fit_client.py -n 0（27 passed）

## 実装詳細

### 追加ファイル
- `src/pptx_generator/pipeline/mapping/llm_fit.py`: LLM クライアント（OpenAI/Azure/Anthropic/AWS Claude/Mock）
- `tests/pipeline/mapping/test_llm_fit_client.py`: LLM クライアントのユニットテスト

### 変更ファイル
- `src/pptx_generator/pipeline/mapping/processor.py`: `_apply_capacity_controls` で LLM fit 実行
- `src/pptx_generator/pipeline/mapping/step.py`: ai_patch_count のカウント追加
- `src/pptx_generator/pipeline/mapping/types.py`: MappingTextFitRequest/Response 追加
- `tests/pipeline/mapping/test_mapping_step_layout_assignment.py`: LLM fit のテストケース追加

### 動作フロー
1. MappingStep で text_hint (max_lines/max_chars) を超過検知
2. LLM に短縮依頼（最大3回リトライ）
3. 成功時: ai_patch 記録＋要素を更新
4. 失敗時: 元内容維持＋warning 記録

### UAT結果詳細（aws-claude）
- **ai_patch_count**: 9
- **修正例**:
  - `two_column_detail-01`: 4行 → 1行（「ブランドガイドラインを自動反映し...」）
  - `one_column_detail-01-clone02`: 5行 → 1行（「余白逸脱・フォントサイズ不足...」）
  - `two_column_detail-01-clone01`: 4行 → 2行（動的/静的モードの説明）
- **全スライドで capacity_warnings 記録**
- **warnings**: 「body が許容行数 X を超過しているため LLM で調整します」

## リスク・制約
- LLM の要約で内容が変質する可能性（要レビュー）
- LLM 呼び出しコスト（大量スライド時）
- LLM API 失敗時は元内容維持（フォールバック済み）

## 参照
- Issue: https://github.com/yurake/pptx_generator/issues/542
- PR: https://github.com/yurake/pptx_generator/pull/543
- docs/design/schema/stage-03-mapping.md