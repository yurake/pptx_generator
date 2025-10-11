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

## Phase 1 完了（2025-10-11）

- [x] 設計課題の整理と改善タスク化
  - メモ: PR レビュー中にユーザーから重要な指摘あり（2025-10-11）
  - メモ: 課題を docs/notes/20251011-bullets-anchor-design-issue.md に整理
  - メモ: Phase 1 実装記録を docs/notes/20251011-bullets-anchor-phase1.md に作成
- [x] bullets_anchor 新仕様の実装完了
  - メモ: Slide.bullets_anchor フィールド追加、後方互換性維持
  - メモ: プレースホルダー削除機能実装、テストケース追加
  - メモ: サンプル JSON 作成、CLI 統合テスト 5件すべて成功
- [x] Phase 1 成果の記録
  - メモ: 新仕様導入、後方互換性 100% 維持、テスト・サンプル完備
  - メモ: 設計課題発見と次段階準備完了

## Phase 2 完了（2025-10-11）

- [x] anchor 指定方法の設計見直し
  - メモ: SlideBulletGroup 形式を導入し、グループ単位でアンカーを指定できるよう拡張（2025-10-11）
  - メモ: 複数箇所への bullets 配置に対応し、後方互換性を維持（2025-10-11）
  - メモ: 詳細は docs/notes/20251011-bullets-anchor-phase2.md に整理済み（2025-10-11）
- [x] Issue 作成と設計議論
  - メモ: 改善案（グループ化 vs 後方互換）を議論し、スキーマ更新方針を確定（2025-10-11）
- [x] 改善実装の計画策定
  - メモ: Phase 2 実装計画に基づきモデル・レンダラー・テスト・サンプルを更新（2025-10-11）
  - メモ: Phase 3 移行時のスキーマ更新方針は Issue 議論後に確定予定

## Phase 3 完了（2025-10-11）

- [x] 旧仕様フィールド（SlideBullet.anchor / Slide.bullets_anchor）を削除し、グループ構造へ統一
  - メモ: スキーマ 1.1 で旧形式を ValidationError として扱う
- [x] レンダラー・サンプル・テストを Phase 3 仕様へ刷新
  - メモ: docs/notes/20251011-bullets-anchor-phase3.md を作成
- [x] スキーマ 1.1 公開と移行ガイド整備
  - メモ: 既存の配布物は samples/json のみのため更新済み JSON を周知対象とする（2025-10-11）

## メモ
- 承認メッセージ: 2025-10-10 ユーザー指示「ok」
- 2025-10-11: PR #149 のレビュー中に anchor 指定方法の設計課題が判明
- 設計課題の詳細は docs/notes/20251011-bullets-anchor-design-issue.md を参照
- Phase 3 仕様（スキーマ 1.1）を本ブランチで実装済み。旧形式は ValidationError
- 最新の実装状況と移行方針は docs/notes/20251011-bullets-anchor-phase3.md を参照
