# bullets の anchor 指定方法に関する設計課題

**作成日**: 2025-10-11
**関連**: RM-007 SlideBullet アンカー拡張, PR #149
**ステータス**: 課題整理完了、改善タスク化待ち

## 背景

PR #149 で `SlideBullet` に `anchor` フィールドを追加し、テンプレート内の任意の図形に箇条書きを配置できるようになった。しかし、実装レビュー中にユーザーから重要な指摘があった。

## 現在の実装の問題点

### 問題1: 各 bullet に anchor を指定する冗長性

**現在の仕様:**
```json
{
  "bullets": [
    {"id": "b1", "text": "項目1", "level": 0, "anchor": "Body Left"},
    {"id": "b2", "text": "項目2", "level": 1, "anchor": "Body Left"}
  ]
}
```

**問題:**
- 各 bullet ごとに同じ anchor を繰り返し指定する必要がある
- bullets は「1つのまとまった箇条書きリスト」なので、リスト全体で配置先を指定すべき
- ユーザーが異なる anchor を誤って指定する可能性がある

### 問題2: 複数箇所への bullets 配置ができない

**ユースケース:**
2カラムレイアウトで左右に異なる箇条書きを配置したい場合

```
┌─────────────────────────────┐
│  タイトル: 現状 vs 提案      │
├──────────────┬──────────────┤
│ 【現状】     │ 【提案】     │
│ • 手作業    │ • 自動化     │
│ • 時間かかる │ • 効率的     │
└──────────────┴──────────────┘
```

**現在の実装では実現不可:**
- `bullets: list[SlideBullet]` は1つのリストしか持てない
- 同じスライド内で複数の bullets グループを異なる場所に配置できない

### 問題3: 意味的な不整合

bullets は「短い文章を箇条書きで並べたい」ときに使う要素であり:
- 個々の bullet は「リストの項目」
- リスト全体が「1つの箇条書きブロック」として配置されるべき
- 各項目ごとに配置先を指定するのは意味的に不自然

## 改善案

### 案A: bullets をグループ化（推奨）

**モデル定義:**
```python
class SlideBullet(BaseModel):
    id: str
    text: str = Field(..., max_length=200)
    level: int = Field(0, ge=0, le=5)
    font: FontSpec | None = None
    # anchor フィールドは削除

class SlideBulletGroup(BaseModel):
    anchor: str | None = None
    items: list[SlideBullet]

class Slide(BaseModel):
    # ...
    bullets: list[SlideBulletGroup] = Field(default_factory=list)
```

**JSON 例（単一グループ）:**
```json
{
  "bullets": [
    {
      "anchor": "Body Left",
      "items": [
        {"id": "b1", "text": "項目1", "level": 0},
        {"id": "b2", "text": "項目2", "level": 1}
      ]
    }
  ]
}
```

**JSON 例（複数グループ）:**
```json
{
  "bullets": [
    {
      "anchor": "Body Left",
      "items": [
        {"id": "c1", "text": "現状: 手作業", "level": 0},
        {"id": "c2", "text": "時間がかかる", "level": 1}
      ]
    },
    {
      "anchor": "Body Right",
      "items": [
        {"id": "p1", "text": "提案: 自動化", "level": 0},
        {"id": "p2", "text": "効率的", "level": 1}
      ]
    }
  ]
}
```

**メリット:**
- ✅ 複数箇所に bullets を配置可能
- ✅ anchor の指定が1箇所で済む（冗長性の解消）
- ✅ 意味的に自然（箇条書きグループ単位で配置）
- ✅ anchor 未指定時のフォールバック動作も明確

**デメリット:**
- ⚠️ 破壊的変更（既存の JSON との互換性がない）
- ⚠️ 移行コストが発生

### 案B: 後方互換性を保ちつつ拡張

**モデル定義:**
```python
class SlideBullet(BaseModel):
    id: str
    text: str = Field(..., max_length=200)
    level: int = Field(0, ge=0, le=5)
    anchor: str | None = Field(None, deprecated=True)  # 非推奨として残す
    font: FontSpec | None = None

class SlideBulletsConfig(BaseModel):
    anchor: str | None = None
    items: list[SlideBullet]

class Slide(BaseModel):
    # Union 型で両方受け入れ
    bullets: list[SlideBullet] | list[SlideBulletsConfig] = Field(default_factory=list)
```

**JSON 例（旧形式: 互換性維持）:**
```json
{
  "bullets": [
    {"id": "b1", "text": "項目1", "level": 0}
  ]
}
```

**JSON 例（新形式: グループ化）:**
```json
{
  "bullets": [
    {
      "anchor": "Body Left",
      "items": [
        {"id": "b1", "text": "項目1", "level": 0}
      ]
    }
  ]
}
```

**メリット:**
- ✅ 後方互換性を維持
- ✅ 段階的な移行が可能
- ✅ 既存サンプルやユーザーの JSON がそのまま動作

**デメリット:**
- ⚠️ 実装が複雑（Union 型の処理が必要）
- ⚠️ 2つの形式が混在する期間が発生
- ⚠️ ドキュメントとサンプルの更新が必要

### 案C: 現状維持 + ドキュメント整備

**対応:**
- 現在の実装（各 bullet に anchor）を維持
- 「同じグループの bullets は同じ anchor を指定すること」を明記
- バリデーション追加: 同じスライド内の bullets の anchor が統一されているかチェック

**メリット:**
- ✅ 実装変更なし
- ✅ 互換性の問題なし

**デメリット:**
- ❌ 複数箇所への配置ができない（根本的な解決にならない）
- ❌ 冗長性は解消されない
- ❌ ユーザーが間違えやすい

## 推奨アプローチ

**段階的移行（案B + 将来的に案A）:**

1. **Phase 1: 後方互換を保ちつつ新形式を導入**
   - 案B の実装
   - 新形式のサンプル追加
   - 旧形式は deprecated として警告表示

2. **Phase 2: 移行期間**
   - ドキュメントで新形式を推奨
   - 既存サンプルを新形式に更新
   - ユーザー向け移行ガイド作成

3. **Phase 3: 旧形式の廃止**
   - 次のメジャーバージョンで旧形式を削除
   - 案A の形式に統一

## 影響範囲

### 変更が必要なファイル

- `src/pptx_generator/models.py`: モデル定義の変更
- `src/pptx_generator/pipeline/renderer.py`: bullets 処理ロジックの変更
- `tests/test_renderer.py`: テストケースの追加
- `samples/json/*.json`: サンプル JSON の更新
- `docs/`: ドキュメントの更新

### 考慮事項

- **テンプレート影響**: なし（テンプレート側は変更不要）
- **PDF 出力影響**: なし（レンダリング結果は同じ）
- **API 互換性**: 破壊的変更の可能性あり
- **スキーマバージョン**: `meta.schema_version` の更新が必要か検討

## 次のアクション

1. ✅ この課題を note として記録（本ファイル）
2. ⬜ ToDo にタスクを追加
3. ⬜ Issue を作成して設計を議論
4. ⬜ PR #149 をマージ（現状の実装でリリース）
5. ⬜ 改善版の実装計画を策定

## 参考

- PR #149: feat(renderer): add anchor support for SlideBullet
- Issue #132: ToDo: SlideBullet 要素でテンプレート側のアンカーを指定できるようレンダラーを拡張する
- RM-007: SlideBullet アンカー拡張
