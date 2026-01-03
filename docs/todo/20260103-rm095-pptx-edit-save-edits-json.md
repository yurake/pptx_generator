---
title: rm095 Stage5 edit 適用済み差分JSONの保存
status: todo
assignee: ""
priority: ""
due: ""
related_issue: ""
branch: feat/rm095-stage5-edit
---
関連Issue: #520

## 背景・目的
- Stage5 edit で適用した差分（edits_json/LLM生成）を成果物として保存し、後続の検証や再適用に使えるようにする。

## やること
- edits を JSON で保存する処理を追加する（案: `PPTX_OUTPUT_ROOT/<tx>/edit/<job_id>/applied_edits.json`）。
- /jobs レスポンスの artifacts に JSON の URL を含めるかの仕様を決めて反映（含める前提で OpenAPI/docs も更新）。
- テスト追加（artifacts に JSON が載ること、パスが正しいこと）。

## 方針・メモ
- 入力ソース: `edits` 指定 > `edits_json` 読み込み > LLM 生成の順で決定。最終的に適用した内容をそのまま保存する。
- 出力パス: `PPTX_OUTPUT_ROOT/<transaction_id>/edit/<job_id>/applied_edits.json` を想定。PPTX と同じ階層に配置し artifacts で配信。
- OpenAPI 影響: edit の artifacts に `edits_json_url` を追加する方向で検討。現行 `/jobs/{job_id}/artifacts/{artifact_type}` は pptx/pdf を返すため、JSON は /jobs の artifacts フィールドに URL を含めて GET 取得とする。
- ロールバック: 保存処理と artifacts/schema 変更を戻せば影響は限定的。

## テスト観点
- /edit ジョブ完了後、出力先に `applied_edits.json` が存在し、内容が適用済み edits と一致する。
- /jobs レスポンス artifacts に JSON URL が含まれる（含める場合）。
- 既存の gen/pdf など他ステージへの影響がないこと。

## ステータス
- [ ] 設計
- [ ] 実装
- [ ] テスト
- [ ] ドキュメント
