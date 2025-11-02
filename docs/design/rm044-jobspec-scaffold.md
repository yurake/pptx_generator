# RM-044 ジョブスペック雛形自動生成 設計メモ

## 目的と出力物
- 工程2 (`pptx tpl-extract`) の成果物としてテンプレート依存情報のみをまとめた `jobspec.json` を追加する。
- 既存の `template_spec.json`・`branding.json` と同一ディレクトリ (`.pptx/extract/`) に保存し、工程3 以降がテンプレ構造を参照できるようにする。
- 雛形は章構成や本文コンテンツを含めず、レイアウトとプレースホルダー情報の catalog として機能する。

## jobspec.json スキーマ案
```jsonc
{
  "meta": {
    "schema_version": "0.1",
    "template_path": "samples/templates/templates.pptx",
    "template_id": "templates",
    "generated_at": "2025-11-02T12:34:56Z",
    "layout_count": 24
  },
  "slides": [
    {
      "id": "title-01",
      "layout": "Title",
      "sequence": 1,
      "placeholders": [
        {
          "anchor": "Title",
          "kind": "text",
          "placeholder_type": "TITLE",
          "shape_type": "SlidePlaceholder",
          "is_placeholder": true,
          "bounds": {
            "left_in": 1.02,
            "top_in": 1.47,
            "width_in": 10.0,
            "height_in": 2.5
          },
          "sample_text": "提案表紙A",
          "notes": []
        }
      ]
    }
  ]
}
```

### フィールド詳細
- `meta.schema_version`: 雛形専用のバージョン。初期値は `0.1`。
- `meta.template_path`: 入力テンプレートへの相対パスまたは絶対パス文字列。
- `meta.template_id`: `layout-validate` と同じ派生ルール（テンプレートファイル名の正規化）。
- `meta.generated_at`: ISO8601 形式の UTC タイムスタンプ。
- `meta.layout_count`: 抽出したレイアウト数。
- `slides`: テンプレート内の各レイアウトを 1 レコードとして収集。
  - `id`: レイアウト名をスラッグ化して連番を付与（例: `title-01`）。
  - `layout`: PPTX 上のレイアウト名。
  - `sequence`: 同名レイアウト内での通番（1 始まり）。
  - `placeholders`: 図形・プレースホルダー情報の一覧。
    - `anchor`: 図形名（アンカー名）。
    - `kind`: `text` / `image` / `table` / `chart` / `other`。`placeholder_type` と `shape_type` から推定する。
    - `placeholder_type`: PPTX のプレースホルダー種別。無い場合は `null`。
    - `shape_type`: python-pptx が持つ図形型名。
    - `is_placeholder`: プレースホルダーかどうか。
    - `bounds`: 左上位置とサイズ（インチ）。
    - `sample_text`: テンプレートに初期テキストが入っている場合のみ格納。
    - `notes`: Analyzer やレイアウト検証で得た警告を格納予定（現段階では空配列）。

## 生成ロジック（TemplateExtractor 拡張）
1. テンプレートから既存 `TemplateSpec` を取得。
2. レイアウトごとにスラッグ化関数でスライド ID を生成。既存 `LayoutValidationSuite._slugify_layout_name` と同等の正規化ロジックをユーティリティへ切り出して再利用する。
3. 図形ごとに `kind` を推定するマッピングを実装。
   - `placeholder_type` が `PICTURE`/`BODY`/`TITLE`/`SUBTITLE` 等の場合に応じて `text` または `image` を割り当て。
   - `shape_type` が `Picture` 系、`Chart` 系であれば直接 `image`/`chart`。
   - 該当なしは `other` とし、利用側が明示的な対応を判断できるようにする。
4. 抽出した情報を `JobSpecScaffold`（新規 Pydantic モデル）へ蓄積。
5. CLI から `jobspec.json` を `ensure_ascii=False` で出力する。

## CLI 連携
- `pptx tpl-extract` 実行時に `.pptx/extract/jobspec.json` を追加で書き出す。
- 出力完了メッセージに `jobspec.json` のパスとスライド件数を追記する。
- エラー時は既存の例外処理を踏襲し、jobspec 生成途中で失敗しても CLI 全体をエラー終了させる。

## テスト戦略
- シリアライズ結果を Pydantic モデル経由で検証するユニットテストを追加。
- CLI 統合テストで `jobspec.json` の存在確認とキーセット検証を実施。
- 代表的なテンプレート（`samples/templates/templates.pptx`）を用いて、`kind` 判定と位置情報が欠落していないことをチェックする。

## ロールバック方法
- `JobSpecScaffold` モデルと生成ロジックを削除し、`pptx tpl-extract` の出力リストから `jobspec.json` を除外すれば従来の挙動に戻る。
