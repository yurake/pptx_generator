---
目的: samples/skeleton.pptx をテンプレートとして PPTX を生成できることを確認する
担当者: yurak
関連ブランチ: feat/sample-potx-validation
期限: 2025-10-12
関連Issue: #13 https://github.com/yurake/pptx_generator/issues/13
---
<!-- Archived: 2025-10-05T17:17:04Z after merge PR #14 -->
<!-- Status: Completed -->

- [x] ブランチ作成
- [x] Issue 作成
  - メモ: Issue #13 を参照（samples/skeleton.potx のPPTX生成検証 / .potx→.pptx 差異要確認）
- [x] サンプルテンプレートの配置とパス確認
  - メモ: samples/skeleton.pptx が参照可能であることを確認
- [x] サンプル仕様で CLI を実行
  - メモ: `uv run pptx-generator run` で --template オプションを指定
- [x] 出力 PPTX の内容確認
  - メモ: レイアウト・フォント・画像が期待通りかチェック
- [x] 結果をドキュメントへ記録
  - メモ: レビューで指摘された内容を記録
- [x] PR 作成
  - メモ: PR #14 https://github.com/yurake/pptx_generator/pull/14 を作成し本文へ反映済

## メモ
- CLI 実行時は作業ディレクトリ `.pptxgen` を使用する

## 実行結果サマリ
- Branch: feat/sample-potx-validation
- Template: samples/skeleton.pptx (md5 短縮: a3b69b1...)
- Command: uv run pptx-generator run samples/sample_spec.json --template samples/skeleton.pptx
- Output: .pptxgen/outputs/proposal.pptx (size=661391, md5=6a929fd7...)
- Notes: 詳細所見は docs/notes/20251005-sample-potx-validation.md / Issue 未作成
