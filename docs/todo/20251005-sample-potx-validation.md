---
目的: samples/skeleton.pptx をテンプレートとして PPTX を生成できることを確認する
担当者: yurak
関連ブランチ: feat/sample-potx-validation
期限: 2025-10-12
関連Issue: 未作成
---

- [x] ブランチ作成
- [ ] Issue 作成
  - メモ: 未作成: 後続でテンプレート検証 Issue を新規登録予定 (作成後に番号と URL を記録)
- [x] サンプルテンプレートの配置とパス確認
  - メモ: samples/skeleton.pptx が参照可能であることを確認
- [x] サンプル仕様で CLI を実行
  - メモ: `uv run pptx-generator run` で --template オプションを指定
- [x] 出力 PPTX の内容確認
  - メモ: レイアウト・フォント・画像が期待通りかチェック
- [x] 結果をドキュメントへ記録
  - メモ: docs/notes/ か当 ToDo に検証結果を残す

## メモ
- CLI 実行時は作業ディレクトリ `.pptxgen` を使用する

## 実行結果サマリ
- Branch: feat/sample-potx-validation
- Template: samples/skeleton.pptx (md5 短縮: a3b69b1...)
- Command: uv run pptx-generator run samples/sample_spec.json --template samples/skeleton.pptx
- Output: .pptxgen/outputs/proposal.pptx (size=661391, md5=6a929fd7...)
- Notes: 詳細所見は docs/notes/20251005-sample-potx-validation.md / Issue 未作成
