# SlideBullet anchor 設計見直し Phase 1 実装記録

**作成日**: 2025-10-11  
**関連**: RM-007 SlideBullet アンカー拡張, PR #149  
**Phase**: Phase 1 完了記録  

## 概要

SlideBullet 要素でテンプレート側のアンカーを指定できるようレンダラーを拡張する Phase 1 実装が完了しました。本記録では実装内容、成果、および次段階への準備状況をまとめます。

## Phase 1 実装内容

### 1. bullets_anchor 新仕様の導入

**導入経緯:**
- 従来は各 [`SlideBullet`](src/pptx_generator/models.py) に個別の `anchor` を指定する必要があった
- bullets は「1つのまとまった箇条書きリスト」なので、リスト全体で配置先を指定すべき
- 冗長性の解消とユーザビリティ向上を目的として新仕様 `bullets_anchor` を導入

**実装仕様:**
```python
class Slide(BaseModel):
    bullets_anchor: str | None = None  # 新フィールド追加
    bullets: list[SlideBullet] = Field(default_factory=list)
```

**JSON 例:**
```json
{
  "bullets_anchor": "Body Left",
  "bullets": [
    {"id": "b1", "text": "項目1", "level": 0},
    {"id": "b2", "text": "項目2", "level": 1}
  ]
}
```

### 2. 後方互換性維持の実装方針

**実装戦略:**
- 既存の [`SlideBullet.anchor`](src/pptx_generator/models.py) フィールドは非推奨として残存
- 新旧両方式に対応する優先順位ロジックを実装
- 段階的移行を可能にする設計

**優先順位ロジック:**
1. `bullets_anchor` が指定されている場合 → 新仕様を使用
2. `bullets_anchor` が未指定 & `bullet.anchor` が指定 → 旧仕様を使用（警告表示）
3. 両方未指定 → 従来の BODY プレースホルダー動作

**実装箇所:**
- [`src/pptx_generator/pipeline/renderer.py`](src/pptx_generator/pipeline/renderer.py) の `_render_bullets()` メソッド

### 3. プレースホルダー削除機能の実装

**問題:**
- アンカー指定時にプレースホルダーが残ってしまう問題があった

**解決:**
- 新しいテキストボックス作成後に元のプレースホルダーを削除する機能を実装
- [`renderer.py`](src/pptx_generator/pipeline/renderer.py) に `_remove_placeholder_if_exists()` メソッドを追加

### 4. テストケース追加

**追加されたテストケース:**
- `test_renderer_removes_bullet_placeholder_when_anchor_specified`: アンカー指定時のプレースホルダー削除を検証
- 後方互換性テスト: 新旧両仕様の動作確認
- CLI 統合テスト: 5件すべてで成功を確認

**テスト対象:**
- [`tests/test_renderer.py`](tests/test_renderer.py)
- [`tests/test_cli_integration.py`](tests/test_cli_integration.py)

### 5. サンプルファイル作成

**新規サンプル:**
- Phase 1 当時は `samples/json/sample_spec_with_bullets_anchor.json` を作成
- Phase 3 で `samples/json/sample_spec.json` に統合済み

## Phase 1 の成果

### ✅ 完了した項目

1. **仕様設計・実装**: `bullets_anchor` 新仕様の完全実装
2. **後方互換性**: 既存の JSON が動作し続けることを保証
3. **テスト追加**: 新機能と後方互換性の両方をカバー
4. **サンプル作成**: 実用的な使用例を提供
5. **PR 提出**: PR #149 が正常に作成・レビュー完了

### 📊 実装結果

- **コード変更**: [`models.py`](src/pptx_generator/models.py), [`renderer.py`](src/pptx_generator/pipeline/renderer.py)
- **テスト追加**: 新規テストケース 3件
- **サンプル追加**: 新仕様デモ用 JSON 1件
- **後方互換性**: 100% 維持（既存サンプルすべて動作）

## 発見された設計課題

Phase 1 実装完了後のレビューで以下の根本的な設計課題が判明しました：

### 主要課題

1. **複数箇所への bullets 配置不可**: 同じスライド内で複数の bullets グループを異なる場所に配置できない
2. **意味的な不整合**: bullets は箇条書きグループとして扱うべきだが、現在は平坦なリスト構造
3. **将来拡張の制約**: 現在の設計では柔軟な配置パターンに対応困難

### 課題記録

詳細な課題分析は [`docs/notes/20251011-bullets-anchor-design-issue.md`](docs/notes/20251011-bullets-anchor-design-issue.md) に記録済み。

## Phase 2 への移行準備状況

### 🟡 準備完了項目

1. **設計課題の整理**: 根本的な問題点と改善案を文書化
2. **段階的移行計画**: Phase 1 → Phase 2 → Phase 3 の戦略を策定
3. **改善案の比較検討**: 3つのアプローチ（グループ化、後方互換拡張、現状維持）を評価

### 📋 Phase 2 で必要な作業

1. **Issue 作成**: 設計議論のための GitHub Issue 作成
2. **改善実装**: bullets グループ化の実装
3. **ドキュメント整備**: 新仕様の利用ガイド作成
4. **移行支援**: 旧仕様から新仕様への移行ツール検討
5. **ユーザー通知**: 廃止予告とマイグレーションガイド

### 🎯 推奨アプローチ

**段階的移行戦略（案B + 将来的に案A）:**
- Phase 2: 後方互換を保ちつつ bullets グループ化を導入
- Phase 3: 旧仕様の段階的廃止
- 詳細は [`design-issue.md`](docs/notes/20251011-bullets-anchor-design-issue.md) の「推奨アプローチ」を参照

## 影響範囲と今後の考慮事項

### 技術的影響

- **テンプレート**: 変更不要（anchor 名の互換性維持）
- **PDF 出力**: 影響なし（レンダリング結果は同等）
- **API 互換性**: Phase 1 では完全互換、Phase 2 以降で破壊的変更の可能性

### スキーマバージョン

- Phase 1: `schema_version` 更新なし（後方互換のため）
- Phase 2 以降: 新機能導入時にバージョン更新を検討

## まとめ

Phase 1 では当初の目標（アンカー指定機能の実装）を完全に達成し、後方互換性も維持しました。しかし、実装レビューを通じてより根本的な設計改善の必要性が明らかになりました。

Phase 2 では判明した設計課題に対処し、より柔軟で使いやすい bullets 機能を提供する予定です。Phase 1 の実装は暫定版として動作し、段階的移行の基盤として活用されます。

## 参考リンク

- **PR #149**: feat(renderer): add anchor support for SlideBullet
- **Issue #132**: ToDo: SlideBullet 要素でテンプレート側のアンカーを指定できるようレンダラーを拡張する  
- **設計課題詳細**: [`docs/notes/20251011-bullets-anchor-design-issue.md`](docs/notes/20251011-bullets-anchor-design-issue.md)
- **ToDo**: [`docs/todo/20251010-renderer-slidebullet-anchor.md`](docs/todo/20251010-renderer-slidebullet-anchor.md)
