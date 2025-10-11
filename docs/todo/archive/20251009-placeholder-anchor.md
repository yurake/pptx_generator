---
目的: プレースホルダー名称をアンカーとして扱えるようレンダラーを拡張する
関連ブランチ: 未作成
関連Issue: #130
roadmap_item: RM-008 カスタムテンプレート操作性向上
---

- [x] まずはブランチ作成
- [x] プレースホルダーと図形アンカーの併用要件を整理し、既存実装との差分を設計する
- [x] レンダリング処理でプレースホルダー名を保持・参照できるように改修する
  - メモ: プレースホルダー削除を避けるだけでなく、チャート／画像の追加後も既存プレースホルダーを壊さないようにする
- [x] サンプルテンプレート（templates/templates*.pptx）を用いて回帰テストを追加し、チャート・画像・テーブルでアンカー指定が機能することを検証する
- [x] ドキュメント（docs/policies/config-and-templates.md 等）にプレースホルダー命名の運用ガイドを追記する
- [x] PR 作成
  - メモ: PR #141 https://github.com/yurake/pptx_generator/pull/141（2025-10-10 完了）

## メモ
- 現状は図形名だけがアンカーに使われるため、プレースホルダーを利用した柔軟なレイアウトが難しい。
- プレースホルダーの名称はスライド生成後に既定名へ変換される可能性があるため、ID ベースでの追跡やレイアウト段階でのメタデータ保持が必要。
- 再現例: `samples/sample_spec.json` の `"anchor": "Body Left"` を指定し、`uv run pptx-generator run samples/sample_spec.json --template samples/templates/templates.pptx --workdir .pptxgen/full3` を実行すると、Two Column Detail レイアウトのプレースホルダーが `Content Placeholder 2` へ変換され、チャートがフォールバック位置に挿入される。
- 設計メモ: `docs/notes/20251009-placeholder-anchor-design.md`
- 実行環境メモ: `UV_CACHE_DIR=.uv-cache` を付けるとサンドボックス環境でも `uv run` 系が動作しやすい。
