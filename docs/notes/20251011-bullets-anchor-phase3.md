# SlideBullet anchor 設計見直し Phase 3 実装記録

**作成日**: 2025-10-11  
**関連**: RM-007 SlideBullet アンカー拡張  
**ステータス**: Phase 3 完了

## 概要

Phase 3 では暫定的に残していた旧仕様を廃止し、`SlideBulletGroup` ベースの箇条書きモデルへ全面移行した。テンプレート上の複数アンカー対応を標準化し、JSON スキーマバージョンを 1.1 へ更新した。

## 実装内容

### 1. モデル統一

- `Slide.bullets` を `list[SlideBulletGroup]` のみに制限。
- `SlideBullet.anchor` と `Slide.bullets_anchor` を削除し、余分なフィールドは ValidationError を返すよう `extra="forbid"` を設定。
- グループの `items` が空配列の場合に検証エラーとなるバリデーションを追加。

### 2. レンダラー更新

- 箇条書き描画処理をグループ前提に簡素化し、旧形式判定ロジックを撤廃。
- グループごとのアンカー重複を検出してエラーを返し、テンプレートの図形名の一意性を保証。
- アンカー未指定グループは本文プレースホルダーへ統合する既定動作を維持。

### 3. テスト・サンプル刷新

- 旧仕様向けテストを削除し、新仕様専用のレンダリング・バリデーションテストを追加。
- グループ形式のサンプル JSON は `samples/json/sample_spec.json` に一本化。
- 旧形式 JSON が ValidationError となることを検証するテストを追加。

## 影響範囲

- JSON の互換性: 旧仕様（`SlideBullet.anchor` など）を使用したファイルはスキーマ 1.1 では検証エラーとなる。移行時は `SlideBulletGroup` 構造へ書き換える必要がある。
- テンプレート: アンカー名の運用は Phase 2 と同様、複数箇所で利用する際は図形名の一意性を保つこと。
- CLI: 既存の CLI 操作フローは変更なし。新スキーマのサンプルを `uv run pptx-generator run samples/json/sample_spec.json` で確認可能。

## 今後のタスク

- Phase 2 から持ち越した設計レビュー Issue の作成と議論。
- スキーマ 1.1 の周知およびマイグレーションガイド整備。

## 参考

- Phase 1 記録: `docs/notes/20251011-bullets-anchor-phase1.md`
- Phase 2 記録: `docs/notes/20251011-bullets-anchor-phase2.md`
- 設計課題整理: `docs/notes/20251011-bullets-anchor-design-issue.md`
