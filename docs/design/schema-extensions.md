# JSON スキーマ拡張メモ

## 目的
- PPTX 生成の表・グラフ対応に向けて入力仕様を拡張する。
- 承認フローおよびマッピング工程で利用する中間 JSON の構造を整理する。
- 今後のレンダリング / 診断ステップ拡張の前提を明確化する。

## 1. スライド入力に関する拡張（2025-10-05）
- `slides[].tables`: テーブル構造を定義。
  - `columns`: 表ヘッダの文字列リスト。
  - `rows`: 行データ。セルは文字列または数値を許容。
  - `style`: `header_fill` (任意), `zebra` (bool)。
- `slides[].charts`: グラフ構成を定義。
  - `type`: `column` などの文字列。描画実装時にサポート種別を定義。
  - `categories`: 軸ラベル。
  - `series`: シリーズごとの名前・値・色 (`color_hex`)。
  - `options`: `data_labels`、`y_axis_format` など追加設定。

## 実装ポイント
- `src/pptx_generator/models.py` にモデル (`SlideTable`, `SlideChart`, ほか) を追加。
- カラーフィールドは既存 `FontSpec` に倣って `#` 有無を統一整形。
- サンプル仕様 (`samples/json/sample_spec.json`) にテーブルとグラフの例を追加。
- 単体テスト (`tests/test_models.py`) で新フィールドが読み込めることを検証。

## 2. 承認・マッピング用中間 JSON（2025-10-11）
工程 3〜6 で利用する中間データのスキーマ概要を以下に記載する。詳細設計は `docs/notes/20251011-roadmap-refresh.md` を参照。

### 2.1 content_draft / content_approved
```jsonc
{
  "slides": [
    {
      "id": "s01",
      "intent": "市場動向",
      "type_hint": "content",
      "elements": {
        "title": "市場環境の変化",
        "body": ["国内需要は前年比12%増", "海外市場は為替影響で横ばい"],
        "table_data": { "headers": [...], "rows": [...] },
        "note": "為替前提は110円/ドル"
      },
      "ai_review": {
        "grade": "B",
        "issues": [{"code": "text_too_long", "message": "..."}],
        "autofix_proposals": [{"patch_id": "p01", "description": "..."}]
      }
    }
  ],
  "meta": {
    "tone": "formal",
    "audience": "management",
    "summary": "..."
  }
}
```
- `content_draft.json`: AI が生成した初稿。`ai_review` の `autofix_proposals` は適用候補パッチ。
- `content_approved.json`: HITL 承認後の確定版。承認済みスライドはロックされ、`applied_autofix` を記録する。
- 承認イベントは `content_review_log.json` に `slide_id`, `action`, `actor`, `timestamp`, `patch_id` を記録。

### 2.2 draft_draft / draft_approved
```jsonc
{
  "sections": [
    {
      "name": "市場概況",
      "slides": [
        {"ref_id": "s01", "layout_hint": "overview", "locked": true, "status": "approved"}
      ]
    }
  ],
  "meta": {
    "target_length": 12,
    "structure_pattern": "report"
  }
}
```
- `layout_hint` は工程 5 のレイアウト選定に利用する。
- 承認ログは `draft_review_log.json` に記録し、付録送りや章移動を差分で保存。

### 2.3 rendering_ready / mapping_log
```jsonc
{
  "slides": [
    {
      "layout_id": "overview_1col",
      "elements": {
        "title": "...",
        "body": ["..."],
        "table_data": {...},
        "note": "..."
      },
      "meta": {
        "section": "市場概況",
        "page_no": 2,
        "sources": ["s01"]
      }
    }
  ]
}
```
- `rendering_ready.json` は `layout_id` とプレースホルダ割付後の要素を保持。
- `mapping_log.json` にはレイアウト候補得点、縮約・分割・付録送りなどのフォールバック結果、AI 補完の採否を記録する。

### 2.4 rendering_log / audit_log
- `rendering_log.json`: レンダリング時の警告（空 PH、layout ミスマッチ）、挿入要素数、処理時間などを記録。
- `audit_log.json`: LibreOffice など後工程のメタデータを従来どおり出力。HITL と関連づけるため `content_review_log`・`draft_review_log` のハッシュを含める。

## 3. 今後のタスク
- 承認 UI / AI レビューの詳細仕様を `docs/requirements/overview.md` と `docs/policies/task-management.md` に反映する。
- `models.py` に各中間 JSON の `pydantic` モデルを追加し、`tests/` でスキーマ検証を行う。
- レンダラーでテーブル・グラフ描画を実装し、スタイル適用ルールを詰める。
- 診断ステップでテーブル/グラフの配置・サイズ・フォントを評価するロジックを検討。
- ドキュメント (README など) に新しい JSON 例を反映する。
