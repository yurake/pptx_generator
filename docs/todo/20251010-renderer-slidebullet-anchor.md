---
目的: SlideBullet 要素でテンプレート側のアンカーを指定できるようレンダラーを拡張する
関連ブランチ: feat/renderer-slidebullet-anchor
関連Issue: #132
roadmap_item: RM-007 SlideBullet アンカー拡張
---

- [x] まずはブランチ作成
- [x] 現行 SlideBullet 描画処理とテンプレートレイアウトのアンカー可否を調査する
  - メモ: レイアウト名と図形名の突合ロジック、BODY プレースホルダー前提の部分を洗い出す
- [x] アンカー指定を JSON 仕様に追加し、レンダラーで図形選択を切り替えられるよう実装する
  - メモ: 既存仕様との互換性維持のためアンカー未指定時は従来動作を維持する
- [x] サンプルとドキュメント、テストを更新して動作を確認する
  - メモ: CLI 統合テスト 5件すべて成功。anchor 未指定時の後方互換性を確認
- [x] プレースホルダー/図形からコンテンツに差し替えた後に元オブジェクトを削除する仕様改修を検討する
  - メモ: SlideBullet でアンカー指定時のプレースホルダー削除機能を実装完了（2025-10-11）
  - メモ: 新しいテキストボックス作成後にプレースホルダーを削除する方式で実装
  - メモ: テストケース追加済み（test_renderer_removes_bullet_placeholder_when_anchor_specified）
- [x] PR 作成
  - メモ: PR #149 https://github.com/yurake/pptx_generator/pull/149（2025-10-11 完了）
- [ ] 設計課題の整理と改善タスク化
  - メモ: PR レビュー中にユーザーから重要な指摘あり（2025-10-11）
  - メモ: 課題を docs/notes/20251011-bullets-anchor-design-issue.md に整理
- [ ] anchor 指定方法の設計見直し
  - メモ: 現在は各 bullet に anchor を指定する仕様だが、bullets グループ全体に指定すべき
  - メモ: 複数箇所への bullets 配置ができない問題を解決する必要あり
  - メモ: 後方互換性を考慮した段階的移行を検討
- [ ] Issue 作成と設計議論
  - メモ: 改善案（グループ化 vs 後方互換）を Issue で議論
  - メモ: スキーマバージョン更新の必要性を検討
- [ ] 改善実装の計画策定
  - メモ: Phase 1（後方互換実装）→ Phase 2（移行期間）→ Phase 3（統一）
  - メモ: 影響範囲: models.py, renderer.py, tests, samples, docs

## メモ
- 承認メッセージ: 2025-10-10 ユーザー指示「ok」
- 2025-10-11: PR #149 のレビュー中に anchor 指定方法の設計課題が判明
- 設計課題の詳細は docs/notes/20251011-bullets-anchor-design-issue.md を参照
- 現在の実装（各 bullet に anchor）は暫定版として PR #149 でマージ予定
- 改善版の実装は別 PR で対応する方針
