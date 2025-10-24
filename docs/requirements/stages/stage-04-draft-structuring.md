# 工程4 ドラフト構成設計 (HITL) 要件詳細

## 概要
- 承認済みコンテンツを章立て・スライド順に配置し、`layout_hint` を確定させる。
- HITL 承認により構成をロックし、後続工程に安定した入力を提供する。

## 入力
- 工程3の `content_approved.json`（`story.phase` / `story.chapter_id` / `story.angle` を含む）。
- 工程2の `layouts.jsonl`（利用可能なレイアウトカテゴリのヒント）。
- 制約情報（本編枚数上限、章構成テンプレ、付録方針）。
- 章テンプレ定義 (`config/chapter_templates/*.json`) と構成テンプレ適用ポリシー。
- Analyzer 連携データ（`analysis_summary.json` など工程6の集計結果）。
- 差戻し理由テンプレート辞書 (`return_reasons.json`)。

## 出力
- `draft_approved.json`: 章構成、スライド順、`layout_hint`、付録フラグ。
- 承認ログ: 章/スライド単位の承認・差戻し履歴。
- レイアウト候補一覧と選定理由を含む提案ログ。
- `draft_meta.json`: 章テンプレ適合率、Analyzer 指摘件数、差戻し理由コード別集計。
- 差戻しテンプレート辞書（`return_reasons.json`）と Draft ログのテンプレ紐付け。
- Analyzer 連携ログ（最新 `analysis_summary.json` の取り込み時刻と結果）。

## ワークフロー
1. Draft API / CLI が章レーンとスライドカードの構成データを提示する。
2. AI が提案する構成案をベースに、人が CLI / 外部ツールから順序や章を調整する。
3. `layout_hint` を選択し、必要に応じて付録送りや統合を行う。
4. 承認単位（章・スライド）で承認フラグを更新し、差戻し理由を記録する。
5. 承認完了後に `draft_approved.json` を出力し、工程5へ渡す。

## 品質ゲート
- すべてのスライドが章に所属し、章順が定義されている。
- 工程3のストーリーフェーズ情報と章構成が整合している（不一致は差戻しまたは章調整を実施）。
- `layout_hint` が未設定のスライドが存在しない。
- 本編枚数が制約内に収まっている（超過は付録へ移動済み）。
- 承認ログが揃い、差戻し理由が空欄でない。

## ログ・連携
- 承認イベントログと工程3ログを `slide_uid` で突合可能にする。
- レイアウト候補のスコア（用途タグ一致率、容量適合度、多様性）を記録する。
- 付録送り・統合の履歴を残し、後続のマッピングで参照する。
- Analyzer 指摘サマリを章・スライド単位で保存し、差戻しテンプレートと相互参照できるようにする。
- 章テンプレ適用結果（適合率、過不足スライド）をメタ情報として保持する。

## RM-036 追加要件
- 章テンプレプリセット: `structure_pattern` ごとにテンプレ ID を定義し、Draft API / CLI が章候補・過不足・適合率を表示する。`draft_*` には `chapter_template_id` と `template_match_score` を章単位で記録する。
- layout_hint インテリジェンス: Layout Hint Engine が候補ごとに `layout_score_detail`（用途タグ・容量・多様性・Analyzer 支援度）を算出し、CLI と Dashboard が理由を提示できるようにする。
- 差戻し理由テンプレート: 差戻し時に `return_reason_code` を必須化し、任意の補足コメントを `return_reason_note` に分離する。コードはテンプレ辞書で管理し、ログで集計可能にする。
- Analyzer 連携: スライド単位の Analyzer 指摘件数を Draft ダッシュボードへ表示し、重大度順に差戻しテンプレート候補を優先表示する。`analyzer_summary` を Draft メタへ出力する。
- HITL UX への反映: 章テンプレ・layout_hint 候補・差戻し理由コードを CLI / API から取得できるようインターフェースを拡張する。PoC では CLI 表示と JSON 出力の整合確認を行う。
- CLI 機能拡張: `--show-layout-reasons`, `--return-reasons`, `--import-analysis`, `--chapter-template` などのオプションを提供し、PoC では標準出力と JSON 出力の両方で新情報を確認できること。
- API 機能拡張: テンプレ辞書・差戻しテンプレ・Analyzer 連携の取得/登録エンドポイントを追加し、既存レスポンスに `layout_score_detail`, `analyzer_summary` 等を含める。

### 章テンプレ辞書仕様
- ファイル配置: `config/chapter_templates/<pattern>/<template_id>.json`
- 必須フィールド: `template_id`, `name`, `structure_pattern`, `required_sections[]`, `constraints`.
- `required_sections[].id` は Draft 章とのマッピングに利用し、重複不可。`min_slides` > 0 の場合は必須章。
- `constraints.max_main_pages` を超過した場合は承認不可または付録送りを促す警告を自動表示。
- 運用要件: テンプレ辞書の更新時はバージョン差分を `docs/policies/config-and-templates.md` に記録し、互換性テストを実施。

### 差戻し理由テンプレ仕様
- 辞書形式: 配列 (`return_reasons.json`) でコードを管理。`code` はシステム内部 ID、`label` は表示名。
- `severity=blocker` のコードが指定された差戻しは再承認までブロック。`severity=warn` は警告表示のみ。
- `related_analyzer_tags` により Analyzer 指摘との紐付けを行い、差戻し UI / CLI で優先表示。
- 運用要件: コードの追加・変更は HITL 運用ポリシーに基づき承認プロセスを実施し、辞書更新時は CLI で自動取得できること。

### Analyzer サマリ連携要件
- 工程6が生成する `analysis_summary.json` の形式を標準化（スライド単位の `severity_counts`, `layout_consistency`, `blocking_tags`, `last_analyzed_at`）。
- Draft 工程は読み込み時にスライド ID の整合性チェックを行い、不一致があれば詳細エラーを返却する。
- analyzer_summary の導入により、差戻しテンプレ候補や layout_hint スコアに Analyzer 情報を反映する。
- 運用要件: `analysis_summary.json` は 24 時間以内のデータを使用し、古いデータは再解析を促す。

## 未実装項目（機能単位）
- 構成管理 API（UI はバックログ）と `layout_hint` 管理機能。
- 多様性を考慮したレイアウト候補スコアリング。
- 付録送り・統合操作の履歴管理と再承認フロー。
- `story_outline` と `layout_hint` の整合チェックおよび警告表示。
- 章テンプレ適用率の算出と `chapter_template_id` の読み書き。
- `layout_score_detail` と `analyzer_summary` を含む候補提示の整備。
- 差戻し理由コード辞書と Draft ログのテンプレ紐付け。

## CLI 支援
- `pptx outline` コマンドは承認済みコンテンツとレイアウト候補を入力に `draft_draft.json` / `draft_approved.json` / `draft_review_log.json` を生成し、章・スライド統計を `draft_meta.json` に出力する。
- `--content-approved` を指定した場合は工程3の成果物を再検証して Spec へ適用したうえで構成計算を実行する。未指定時は Spec に格納された内容をそのまま利用する。
- メタ情報には章ごとの承認状態や付録枚数上限が含まれ、工程5以降の監査ログや再実行時のトレースに活用できる。
