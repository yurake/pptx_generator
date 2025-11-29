---
目的: RM-081 文字数許容量算出とスキーマ反映
関連ブランチ: feat/rm081-text-capacity
関連Issue: #320
roadmap_item: RM-081 文字数許容量算出とスキーマ反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm081-text-capacity を作成し初期コミットを push 済み
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 参照済みドキュメント: docs/policies/context-engineering.md, CONTRIBUTING.md, docs/policies/task-management.md, docs/roadmap/roadmap.md#rm-081, docs/requirements/stages/stage-03-compose.md, docs/design/schema/stage-03-mapping.md, docs/todo/20251124-rm081-text-capacity.md
    - 対象整理（スコープ、対象ファイル、前提）: テンプレ抽出時にタイトル・本文などすべてのテキスト系プレースホルダーからフォント／段落情報（Theme Font 解決含む）を取得して保持し、`text_capacity`（total_chars/char_per_line/max_lines）を算出して JobSpec/SlideTextbox/LayoutValidation へ伝搬。branding.json のフォント依存を廃止しテンプレ設定を単一ソースとする。
    - ドキュメント／コード修正方針: `src/pptx_generator/models.py` を拡張して `font` と `text_capacity` を正式フィールド化し、`spec_loader.py`・`generate_ready.py`・`pipeline/template_extractor.py`・`layout_validation/{schema.py,suite.py}`・Renderer/Analyzer/CLI 設定を更新。`branding.json` からフォント関連キーを削除し、README/requirements/design/policies/roadmap/ToDo に反映。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan と承認情報を本 ToDo へ記録し、docs/notes に議論ログを保存。PR では差分要約とテスト結果を共有。
    - 想定影響ファイル: `src/pptx_generator/models.py`, `spec_loader.py`, `generate_ready.py`, `pipeline/template_extractor.py`, `layout_validation/schema.py`, `layout_validation/suite.py`, `pptx_generator/cli.py`, `pipeline/renderer.py`, `pipeline/analyzer.py`, `utils` 配下新規 `text_capacity` ヘルパー、`branding.json`/関連設定、`samples/` JSON、docs 群。
    - リスク: 既存 JobSpec/GenerateReady との互換性が崩れる恐れ、推定ロジック不整合による text_hint 差異、branding.json 削除に伴う他機能影響。フォールバック値とテストで緩和。
    - テスト方針: `uv run --extra dev pytest tests/template_audit/test_template_extractor_jobspec_output.py`, `uv run --extra dev pytest tests/layout_validation`, 主要レンダリング／CLI 統合テスト（例: `tests/pipeline/render/test_renderer_rich_content.py`, `tests/integration/test_cli_generate_pipeline_flow.py`）。
    - ロールバック方法: 関連コミットを `git revert` し、branding.json へのフォント参照を復元して旧仕様へ戻す。必要なら `text_capacity` 新フィールドを無視するコードパスに切り替え。
    - 承認メッセージ ID／リンク: ユーザー「承認します。この内容をtodoに書いてね。また、ここまでのディスカッションをnoteに要約せず全文そのまま転記してほしい。」
- [ ] 設計・実装方針の確定
  - メモ: 
    - TemplateExtractor で取得した `font`/`paragraph`/`text_capacity` を JobSpec/GenerateReady/Renderer 全体へ伝搬済み。ここからは Renderer・Analyzer・CLI で `branding.json` 依存を撤廃し、テンプレ抽出値と JobSpec メタを唯一のスタイル情報源とする。
    - `generate_ready.meta` へテンプレ既定スタイル（heading/body フォント、段落既定、配色）を埋め込む案を検討し、Renderer/Analyzer で参照する。テンプレ内にスタイルが欠落するケースは TemplateExtractor でのフォールバック値（テーマ or デフォルト）を利用。
    - CLI の `--branding` オプションと `_prepare_branding` 系導線を段階的に削除し、テンプレからの自動抽出結果のみに統一。旧 `config/branding.json` 参照が不可欠な箇所は ToDo へ記録しつつ、必要なら段階的に廃止する方針をユーザーと擦り合わせる。
    - 依存調査メモ:
      - CLI: `pptx compose` / `pptx mapping` / `pptx gen` は `_prepare_branding` → `_load_branding_for_template` で `BrandingConfig` を構築し、Renderer/Analyzer/Refiner へ渡すと同時に `branding` アーティファクトを監査ログへ保存している。`pptx template` では抽出物として `branding.json` を常時出力。
      - Renderer (`src/pptx_generator/pipeline/renderer.py`): タイトル・本文・箇条書きのフォント適用、段落スタイル、テーブル／チャートの配色、アンカー別スタイル解決をすべて `BrandingConfig` 経由で行っている。`resolve_layout_font` / `resolve_layout_paragraph` で `layouts.*.placements.*` を参照。
      - Analyzer (`_build_analyzer_options`)・Refiner (`_build_refiner_options`): `BrandingConfig` の body フォントとテーマカラーを既定値として読み取り、フォントサイズしきい値やカラー調整の初期値を決定。Analyzer の背景色・コントラスト判定、Refiner のフォント補正に直結。
      - 設定ファイル・テスト: `settings.BrandingConfig.load` を前提とする経路（`config/branding.json`、`tests/config/test_settings_loading.py` 等）が存在。移行後はテンプレ抽出メタをモックする形に差し替える必要あり。
      - branding 抽出: `src/pptx_generator/branding_extractor.py` はテンプレートのテーマ／スライドマスターから配色とフォントを解析し `BrandingExtractionResult` を返す。`BrandingConfig` へ変換する前提なので、テンプレ由来メタへ直結する軽量スキーマに合わせて再設計する。
    - 移行論点:
      - Slide.title / subtitle には現状フォント情報が載らないため、テンプレ抽出時に `SlideTextbox` へ転記するか `generate_ready.meta` 側でヘッダ用スタイルを保持する仕組みが必要。
      - 監査ログ (`audit_log.json`) では `branding.source` にテンプレパスと抽出エラーを記録している。BrandingConfig 廃止後もテンプレ由来スタイルと抽出エラー情報を保持できるよう新メタ形式を用意する。
      - `BrandingConfig.default()` をフォールバックに使っていた箇所は、テンプレテーマ解決が失敗した場合に TemplateExtractor で作成する `theme` 相当値（heading/body フォント、主要カラー）で代替する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 
- [ ] テスト・検証
  - メモ: 
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
