# Stage1 → Stage3 メタデータ受け渡しインターフェース案

## 目的
- Stage1（テンプレ構造抽出）および Stage2（テンプレ検証）で得たメタデータを、Stage3（ドラフト構築・レイアウト推薦）が活用しやすい形で統一する。
- 静的モード（prepare blueprint）の検証や usage_tags 正規化の根拠を Stage3 ログに連携し、手動確認コストを下げる。

## 前提と用語
- **Stage1**: `TemplateExtractor` により `template_spec.json` や Blueprint を生成する工程。
- **Stage2**: `LayoutValidationSuite`（およびテンプレ検証 CLI）が `layouts.jsonl`・`diagnostics.json` を出力する工程。
- **Stage3**: `DraftStructuringStep` と `CardLayoutRecommender` がレイアウト候補を決定する工程。
- **Blueprint**: 静的モード向け slot 定義（`TemplateBlueprint`）。`prepare_generation_meta.mode == "static"` のとき必須。
- **Canonical usage tags**: `config/usage_tags.json` で定義された語彙。全工程で同一タグ集合を利用する。

## アーティファクト間の役割整理
| アーティファクト | 主な生成工程 | 主な利用工程 | 現在含まれる主な項目 | Stage3 への活用ポイント |
| --- | --- | --- | --- | --- |
| `template_spec.json` | Stage1: `TemplateExtractor` | Stage3: `DraftStructuringStep`（静的モード） | レイアウト名、アンカー一覧、`layout_mode`、`blueprint`（静的時） | 静的モード時の slot 定義、アンカー整合性チェック、`template_spec_path` 保存 |
| `layouts.jsonl` | Stage2: `LayoutValidationSuite` | Stage3: `DraftStructuringStep`、`CardLayoutRecommender` | `usage_tags`（ヒューリスティック＋AI）、`placeholder_summary`、`text_hint`、`media_hint`、`blueprint` サマリ | レイアウトスコア算出、AI 推薦への入力、レイアウト診断ログの詳細化 |
| `diagnostics.json` | Stage2: `LayoutValidationSuite` | Stage3: ドラフト構築時の警告確認 | 抽出・検証警告 | Stage3 ログへの挿入候補（将来検討） |
| `prepare_document` 等 | Stage2: `prepare_normalization` | Stage3: `DraftStructuringStep` | 静的モード用カード定義、blueprint ハッシュ | Stage1/2 レイアウト情報との突合 |

## 受け渡しフィールド案
`layouts.jsonl` の 1 レコードを Stage3 で `LayoutProfile` として読み込む前提で、以下フィールドを整理する。

| フィールド | 生成元 | 型 | Stage3 での利用想定 |
| --- | --- | --- | --- |
| `usage_tags` | ヒューリスティック＋Template AI | `string[]` | レイアウト推薦スコア算出。AI 結果が無い場合でも canonical 語彙に正規化されたタグが入ることを保証する。 |
| `heuristic.tags` / `heuristic.reasons` | ヒューリスティック | `string[]` / `string[]` | AI が不在・失敗した際の根拠表示。Stage3 ログの `mapping_log` に転記する。 |
| `placeholder_summary.counts` | Stage1: `TemplateExtractor` → Stage2 集約 | `object`（種別ごとのカウント） | テキスト／ビジュアル比率の簡易判定に利用。 |
| `placeholder_summary.area_ratio` | Stage2 集約 | `object`（種別ごとの面積比） | AI 推薦ペイロードやヒューリスティックスコアで利用予定。 |
| `blueprint.slots[*].slot_id` | Stage1: Blueprint | `string` | 静的モード時の slot 対応確認。 |
| `blueprint.slots[*].required` | Stage1: Blueprint | `bool` | Stage3 の必須プレースホルダ突合。 |
| `blueprint.slots[*].intent_tags` | Stage1: Blueprint | `string[]` | Stage3 ログにレイアウト候補の意図タグを提示。 |
| `meta.heuristic_reason`（新設案） | Stage2（テンプレ検証） | `string` | ヒューリスティック結果の説明をステップログへ表示。 |

> **注記**: `meta` オブジェクトは `layouts.jsonl` のルート直下に追加する想定（例: `{"meta": {"heuristic_reason": "..."}}`）。既存レコードとの互換性を保つため optional フィールドとして設計する。

### 追加フィールド導入ステータス
| フィールド | 現状 | 対応方針 |
| --- | --- | --- |
| `placeholder_summary.counts` | 一部ヒントのみ（種類毎カウントは未保証） | Stage1 側で正規化し Stage2 で欠損補完。 |
| `placeholder_summary.area_ratio` | 未導入 | 面積算出ロジックを Stage2 に追加。 |
| `blueprint.slots[*]` | 静的モード時のみ `TemplateBlueprint` に存在 | Stage2 で Blueprint 情報を `layouts.jsonl` に転記。 |
| `meta.heuristic_reason` | 未導入 | ヒューリスティック実行時に理由をテキスト整形して格納。 |

### JSON 例
```jsonc
{
  "layout_id": "overview__one_col_v1",
  "layout_name": "Overview - 1 Column",
  "usage_tags": ["overview", "content"],
  "heuristic": {
    "tags": ["overview", "content"],
    "reasons": ["title placeholder detected", "body placeholder size=82%"]
  },
  "placeholder_summary": {
    "counts": {"title": 1, "body": 1, "image": 1},
    "area_ratio": {"title": 0.12, "body": 0.68, "image": 0.2}
  },
  "blueprint": {
    "layout": "Overview - 1 Column",
    "slots": [
      {
        "slot_id": "overview__one_col_v1.slot01",
        "anchor": "PH__Title__1",
        "required": true,
        "content_type": "text",
        "intent_tags": ["overview", "title"]
      }
    ]
  },
  "text_hint": {"max_chars": 420, "max_lines": 12},
  "media_hint": {"allow_table": false, "allow_chart": false, "allow_image": true},
  "version": "1.1.0"
}
```

## Stage3 での活用パターン
1. **AI 推薦入力**  
   - `CardLayoutRecommender` の `LayoutAIRequest` 生成時に `usage_tags` と `placeholder_summary`、`blueprint.slots` を同梱し、AI が分類根拠を返せるようにする。
2. **ヒューリスティックスコア**  
   - テキスト容量・ビジュアル比率を `placeholder_summary` から算出し、`DraftLayoutScoreDetail` の `layout_fit` 指標を安定化させる。
3. **静的モード検証**  
   - `DraftStructuringStep` で `blueprint.slots` を基準に `prepare_document.cards[*].slots[*]` を検証し、未充足スロットを `draft_mapping_log.json` に追記する。
4. **診断ログのトレーサビリティ**  
   - `heuristic.reasons` を `mapping_log` の `usage_tag_sources` へ転記し、AI／ヒューリスティックのどちらが採用されたかを可視化する。

## 静的モードとの整合
- `prepare_generation_meta.mode == "static"` の場合、Stage3 は `template_spec.blueprint` を信頼源とする。`layouts.jsonl.blueprint.slots` にも同一の slot 情報を記録し、ID／ハッシュ比較を容易にする。  
- Blueprint ハッシュの突合手順:
  1. Stage3 が `prepare_generation_meta.blueprint_hash` と `TemplateSpec.blueprint` の SHA を比較。
  2. 一致すれば `layouts.jsonl.blueprint.slots` を利用。差異があれば警告ログを出力し、`draft_mapping_log.json` に記録。
- 静的モードの CLI（`pptx prepare --mode static`）では `layouts.jsonl` を参照しない場合があるため、Stage3 で不足するメタデータは `template_spec.blueprint` から補完する。

## 合意事項とレビュー観点
- **タグ整合性**: `usage_tags` は `normalize_usage_tags_with_unknown` 済みの canonical 値のみを許可し、AI／ヒューリスティックいずれの経路でも同一タグ集合が返ること。
- **Blueprint 整合性**: `blueprint.slots[*].slot_id` は `TemplateBlueprintSlot.slot_id` と一致させ、欠損時は Stage3 で警告を出力する。
- **欠損許容**: `placeholder_summary` や `meta.heuristic_reason` は optional とし、欠損時は Stage3 で従来ロジックへフォールバックする。
- **互換性**: 既存 `layouts.jsonl` を読み込む際にエラーが発生しないよう、Schema バージョンを `SUITE_VERSION` と連動させ、`version` フィールドで互換性を宣言する。
- **観測可能性**: Stage3 ログ（`draft_mapping_log.json` など）から AI/ヒューリスティックの採用経緯、Blueprint-slot 充足状況を追跡できることをレビューで確認する。

## 実装フェーズ案
1. **Schema 拡張**: `layouts.jsonl` の JSON Schema と `LayoutProfile` モデルを新フィールドに対応させる。
2. **データ算出**: Stage1/Stage2 で `placeholder_summary`・Blueprint 情報・`heuristic_reason` を生成し、欠損時のフォールバックを整備する。
3. **Stage3 利用**: `DraftStructuringStep`・`CardLayoutRecommender` を更新し、新フィールドをログやスコアリングに組み込む。
4. **監査・テスト**: CLI 統合テストとドキュメントを更新し、静的モード／動的モード双方で差分が無いことを検証する。

## 今後のタスク
1. `LayoutValidationSuite` に `placeholder_summary.area_ratio` や `meta.heuristic_reason` を追加する実装計画を立てる。  
2. `CardLayoutRecommender` と `DraftStructuringStep` で `blueprint.slots` を診断ログへ出力するワークログを整備。  
3. 静的モードでの手動確認手順を `docs/runbooks/pptx-analyzer.md` と `docs/notes/20251122-stage1-metadata-plan.md` に反映。  
4. `layouts.jsonl` の JSON Schema を更新し、CI 検証に新フィールドを追加する。
