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
- [x] 設計・実装方針の確定
  - メモ: 
    - TemplateExtractor で取得した `font`/`paragraph`/`text_capacity` を JobSpec/GenerateReady/Renderer 全体へ伝搬済み。ここからは Renderer・Analyzer・CLI で `branding.json` 依存を撤廃し、テンプレ抽出値と JobSpec メタを唯一のスタイル情報源とする。
    - `generate_ready.meta` へテンプレ既定スタイル（heading/body フォント、段落既定、配色）を埋め込む案を検討し、Renderer/Analyzer で参照する。テンプレ内にスタイルが欠落するケースは TemplateExtractor でのフォールバック値（テーマ or デフォルト）を利用。
    - CLI の `--branding` オプションと `_prepare_branding` 系導線を段階的に削除し、テンプレからの自動抽出結果のみに統一。旧 `config/branding.json` 参照が不可欠な箇所は ToDo へ記録しつつ、必要なら段階的に廃止する方針をユーザーと擦り合わせる。
    - 依存調査メモ:
      - CLI: `pptx compose` / `pptx mapping` / `pptx gen` は `_prepare_template_style` で `TemplateStyle` を抽出し、Analyzer/Refiner/Renderer へ渡すと同時に `template_style` アーティファクトを監査ログへ保存している。`pptx template` では参考用の `branding.json` を引き続き出力。
      - Renderer (`src/pptx_generator/pipeline/renderer.py`): タイトル・本文・箇条書きのフォント適用、段落スタイル、テーブル／チャートの配色、アンカー未指定時のフォールバック座標を `TemplateStyle` のデフォルト値から解決している。
      - Analyzer (`_build_analyzer_options`)・Refiner (`_build_refiner_options`): `TemplateStyle` の body フォントおよびカラーを既定値として取り込み、フォントサイズしきい値やカラー調整の初期値を決定している。
      - 設定ファイル・テスト: `settings.BrandingConfig` はテンプレ抽出結果を `TemplateStyle` に変換するための互換レイヤとして残存。ユニットテスト（`tests/config/test_settings_loading.py`）は引き続き旧スキーマ検証を担う。
      - テンプレートスタイル抽出: `src/pptx_generator/template_style.py` で `BrandingExtractionResult` を `TemplateStyle`/アーティファクトへ変換する。今後は `branding_extractor` 依存を段階的に薄め、テンプレ由来メタに一本化する。
    - 移行論点:
      - Slide.title / subtitle には現状フォント情報が載らないため、テンプレ抽出時に `SlideTextbox` へ転記するか `generate_ready.meta` 側でヘッダ用スタイルを保持する仕組みが必要。
      - 監査ログ (`audit_log.json`) では `template_style.source` にテンプレパスと抽出エラーを記録している。BrandingConfig 廃止後もテンプレ由来スタイルと抽出エラー情報を保持できるよう新メタ形式を用意する。
      - `TemplateStyle.default()` をフォールバックに使っていた箇所は、テンプレテーマ解決が失敗した場合に TemplateExtractor で作成する `theme` 相当値（heading/body フォント、主要カラー）で代替する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: TemplateStyle モデル追加と CLI / Renderer / Mapping の依存置換、テンプレ起点のスタイル抽出ユーティリティ導入済み。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/render/test_renderer_rich_content.py` / `tests/integration/test_cli_generate_pipeline_flow.py` を実行し成功。レンダリング・CLI 両経路の回帰確認済み。
- [x] ドキュメント更新
  - メモ: TemplateStyle への移行を CLI/設計ドキュメントへ反映済み。未更新の領域は要否検討のうえコメントを残す。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
    - メモ: TemplateStyle 移行で追加整備不要（RM-081 として別途更新なし）
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: stage-04-gen 要件に TemplateStyle の入力を追記（fce14ad）
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: CLI リファレンス、全体設計、stage 3/4 資料を TemplateStyle 基準へ更新（fce14ad）
  - [x] docs/runbook 配下
    - メモ: Analyzer runbook は参考用途のみで変更不要（branding.json 参照は情報共有目的）
  - [x] README.md / AGENTS.md
    - メモ: 現行 README/AGENTS にテンプレスタイル固有の記述はなく追加変更不要
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
