# Stage1 メタデータ抽出強化 Plan（2025-11-22）

## 1. 現状整理
- **TemplateExtractor**  
  - `template_spec.json` に `layouts[*].placeholders` / `anchor` / `auto_draw` / Blueprint 情報を出力。  
  - プレースホルダーの要約やレイアウトごとの統計は `template_release.json` 側（release 用メタ）にのみ保持。
- **layout_validation + Template AI**  
  - レイアウト構造（placeholders, text_hint, media_hint）とヒューリスティックス（static_rules）を LLM に渡し、usage_tags を正規化。  
  - LLM 応答が無い場合はヒューリスティック結果のみ。
- **Stage3 連携**  
  - `layouts.jsonl` の 1 行が `LayoutProfile` へ変換され、`usage_tags_rule` / `text_hint` / `media_hint` / `placeholder_summary` を `draft_structuring` が利用。  
  - Blueprint（静的モード）との差異や slot 充足状況は Stage3 内で再計算している。

## 2. 課題
1. レイアウトのプレースホルダー要約（種類・領域・想定用途）が Stage3 まで一貫して伝わっていない。  
2. chart/table 等の取り扱い可否が `media_hint.allow_chart` などに限定され、具体的な slot 情報が乏しい。  
3. Template AI が usage_tags を返さなかった場合のフォールバックデータ（ヒューリスティック説明、推論根拠）が整備されていない。  
4. 静的 Blueprint で slot 毎に収集した metadata（required / anchor / content_type）が Stage3 へ渡る際に集約されておらず、再集計コストが発生。  
5. Stage1 から Stage3 へ渡す JSON が「テンプレ抽出」「テンプレ検証」「Blueprint」の 3 系列に分散しており、必要なメタを把握しづらい。

## 3. 強化方針（案）
### 3.1 Layout メタデータ
- `layouts.jsonl` に以下の追加フィールドを検討:
  - `placeholder_summary.counts`（text / image / table / chart）
  - `placeholder_summary.area`（各アンカーの面積・相対比）
  - `media_capabilities`（chart/table/picture の可否と推奨配置）  
  - `slot_candidates`（静的 Blueprint が存在する場合、対応する slot_id / required / content_type）
- Blueprint 連携: `template_spec.json` blueprint 情報を `layouts.jsonl` へマッピングできるよう、レイアウト名＋slot 情報をハッシュ化して持つ。

### 3.2 Usage tag フォールバック情報
- Template AI から usage tags が得られなかった場合に備え、Stage1 で `heuristic_reason`（ヒューリスティックが判断した根拠）を `layouts.jsonl` に埋め込む。
- Layout AI へのペイロードにも `heuristic_reason` を伝達し、AI が利用できるようにする。

### 3.3 LLM 連携メタ
- Template AI / Layout AI のプロンプトへ以下の情報を含める整理（実装済み内容の明文化）:
  - Intent/Media Tag の説明（usage_tags.json v2.0）  
  - Layout metadata テンプレート（placeholder counts / slot summary）
  - Blueprint 由来の slot 要求（required / optional / note アンカー等）
- Stage1 で LLM を無効化（mock）した場合でも同じ構造の JSON を出力し、Stage3 が差異なく利用できるようにする。

## 4. 対象ファイル
- `src/pptx_generator/pipeline/template_extractor.py`（placeholder summary / slot info 集約）
- `src/pptx_generator/layout_validation/suite.py`（Template AI 呼び出しと `layouts.jsonl` 出力ロジック）
- `src/pptx_generator/template_ai/service.py`（LLM ペイロード生成）
- `docs/design/schema/stage-01-template-preparation.md`（スキーマの更新）
- テスト: `tests/test_template_ai.py`, `tests/test_layout_validation_template_ai.py`, `tests/test_layout_recommender.py`
- **Stage2 静的モード**: `src/pptx_generator/prepare/orchestrator.py` と Blueprint 参照ロジック（slot 情報を Stage2 でも利用するため、追加メタがあれば `template_spec.blueprint` から参照できるよう整合を取る）。

## 5. 次のステップ（実装に向けたタスク）
1. `layouts.jsonl` 拡張項目のスキーマ草案を作成し、Stage3 での利用可否を確認する。  
2. TemplateExtractor でプレースホルダー統計・Blueprint slot 情報を抽出し、`template_spec` / `layouts.jsonl` に反映。  
3. Template AI と Layout AI のペイロード生成コードを更新し、新メタを prompt に含める。  
4. Stage3 側（`draft_recommender.py` / `pipeline/draft_structuring.py`）で新メタを参照し、ログ/診断に活用する。  
5. Stage2 静的モードで Blueprint 追加メタを利用できるよう確認し、必要に応じて `prepare` オーケストレーターへ反映。  
6. テストとドキュメントを更新し、ToDo の実装タスクに反映する。
7. Stage1 → Stage3 メタデータ受け渡し仕様のドラフトを `docs/design/stages/stage1-stage3-metadata-interface.md` に集約し、設計レビューのベースラインとする。

## 6. layouts.jsonl スキーマ更新計画
1. **仕様整理**
   - `docs/design/stages/stage1-stage3-metadata-interface.md` を基準に、追加フィールド（`placeholder_summary.counts/area_ratio`、`blueprint.slots[*]`、`meta.heuristic_reason`）ごとの必須／任意条件を明文化する。
   - JSON Schema 変更案を `docs/design/schema/stage-02-template-structure-extraction.md` に反映し、`SUITE_VERSION` を 1.1.0 に引き上げる草案を作成。
2. **実装タスク分解**
   - Stage1 (`TemplateExtractor`)：Blueprint slot 情報を `LayoutInfo` → `TemplateBlueprint` → `layout_validation` へ伝搬させる。
   - Stage2 (`LayoutValidationSuite`)：  
     - `placeholder_summary` 集約に面積比算出を追加。  
     - `meta.heuristic_reason` をヒューリスティック診断時に付与。  
     - JSON Lines エンコーダを更新し、空値は出力しないよう制御。
   - Stage3 (`draft_structuring.py`, `draft_recommender.py`)：新フィールド読み込みとログ整備、既存テストの期待値更新。
3. **テスト計画**
   - `tests/test_layout_validation_suite.py`：新フィールド出力と schema 検証のケースを追加。  
   - `tests/test_draft_structuring_step.py`：Blueprint slot 連携と `placeholder_summary` フォールバックの挙動を確認。  
   - CLI 統合テスト：`uv run pptx tpl-extract` → `pptx prepare --mode static` の静的フローで新フィールドが利用されることを検証。
4. **移行方針**
   - 旧形式（v1.0.x など）の `layouts.jsonl` はサポートせず、テンプレ抽出／検証を再実行して新フォーマットを生成する。  
   - Stage3 は `SUITE_VERSION` が一致しないレコードをエラー扱いとし、再抽出を促す。  
   - サンプルデータ（`samples/json/sample_template_layouts.jsonl`）とドキュメントは新フォーマットのみを前提に更新する。

## 7. 実装確認（2025-11-23）
- `CardLayoutRecommender._build_layout_metadata` で Stage1 由来メタデータ全体（`placeholder_summary` / `blueprint` / `meta`）を保持するよう更新（`src/pptx_generator/draft_recommender.py`）。
- メタ保持を検証するユニットテストを追加（`tests/test_layout_recommender.py::test_build_layout_metadata_retains_stage1_payload`）。
- Layout AI リクエストに Stage1 メタが渡ることを確認済み（`CardLayoutRecommender._apply_layout_ai` で `_build_layout_metadata` の結果を利用）。
