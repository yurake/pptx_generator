# SlideBullet anchor 設計見直し Phase 2 実装記録

**作成日**: 2025-10-11  
**関連**: RM-007 SlideBullet アンカー拡張  
**ステータス**: Phase 2 実装反映

## 概要

Phase 2 では箇条書きの配置指定をグループ単位に再設計し、同一スライド内で複数アンカーへ bullets を割り当てられるようにした。既存 JSON の互換性を維持しつつ、移行期間中の警告とドキュメント整備を進める。

## 実装内容

### 1. モデル拡張

- `SlideBulletGroup` モデルを追加し、`Slide.bullets` が `list[SlideBullet]` と `list[SlideBulletGroup]` の両方を受け取れるよう更新。
- 旧フィールド `SlideBullet.anchor` は互換用途として残し、スキーマに非推奨フラグを付与。

### 2. レンダラー更新

- グループ形式を判別し、アンカー付きグループごとにテキストボックスを生成する処理へリファクタ。
- アンカー未指定グループは本文プレースホルダーへ集約し、既存のフォールバック動作を維持。
- 複数グループで同一アンカーを指定した場合は明示的にエラーを発生させ、テンプレート側の重複利用を防止。
- グループ形式で個別 `bullet.anchor` が指定された場合は無視される旨の警告を出力。

### 3. テスト・サンプル整備

- `tests/test_renderer.py` にグループ形式で左右のプレースホルダーへ配置する統合テストを追加。
- グループ形式サンプルは Phase 3 で `samples/json/sample_spec.json` に統合。

## 残課題

- GitHub Issue で設計レビューを実施し、残る移行手順（ドキュメント更新、CLI 統合テスト拡充）のスケジュールを確定する。（Phase 3 でも継続）
- Phase 3 で旧形式を廃止する際のスキーマバージョン更新方針を決定する。（Phase 3 で対応済み）

## 参考

- Phase 1 記録: `docs/notes/20251011-bullets-anchor-phase1.md`
- 設計課題整理: `docs/notes/20251011-bullets-anchor-design-issue.md`
