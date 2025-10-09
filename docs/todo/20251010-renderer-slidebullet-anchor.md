---
目的: SlideBullet 要素でテンプレート側のアンカーを指定できるようレンダラーを拡張する
関連ブランチ: feat/renderer-slidebullet-anchor
関連Issue: 未作成
roadmap_item: RM-007 SlideBullet アンカー拡張
---

- [ ] まずはブランチ作成
- [ ] 現行 SlideBullet 描画処理とテンプレートレイアウトのアンカー可否を調査する
  - メモ: レイアウト名と図形名の突合ロジック、BODY プレースホルダー前提の部分を洗い出す
- [ ] アンカー指定を JSON 仕様に追加し、レンダラーで図形選択を切り替えられるよう実装する
  - メモ: 既存仕様との互換性維持のためアンカー未指定時は従来動作を維持する
- [ ] サンプルとドキュメント、テストを更新して動作を確認する
  - メモ: `samples/json/sample_spec.json` へ anchor 付き箇条書き例を追加し、CLI 統合テストで検証する
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- `SlideBullet` 以外のテキスト形状にも拡張が必要かを調査し、スコープを明示する
- LibreOffice PDF 出力や Open XML SDK 仕上げツールへの影響を確認する
