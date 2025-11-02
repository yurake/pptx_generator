# 工程4 マッピング (HITL + 自動) 要件詳細

## 概要
- 承認済みコンテンツを章立て・スライド順へ落とし込み、テンプレ構造に適合させるまでを一気通貫で扱う工程。
- 前半は HITL によるドラフト構成設計（旧工程4）、後半は自動マッピング（旧工程5）で構成する。
- 最終成果物は工程5（レンダリング）が直接受け取る `generate_ready.json` と監査ログ群。

## サブ工程と成果物
| サブ工程 | 区分 | 主な成果物 | 概要 |
| --- | --- | --- | --- |
| 4.1 ドラフト構成 | HITL | `draft_approved.json`, `draft_review_log.json`, `draft_meta.json` | 章構成・スライド順・`layout_hint` を確定し、承認ログとメタ情報を記録する。 |
| 4.2 レイアウトマッピング | 自動 | `generate_ready.json`, `mapping_log.json`, `fallback_report.json` | テンプレ構造とドラフト情報を統合し、プレースホルダ割付とフォールバック履歴を確定する。 |

---

## 4.1 ドラフト構成（HITL）

### 入力
- 工程3の `content_approved.json`（`story.phase` / `story.chapter_id` / `story.angle` を含む）。
- 工程2の `jobspec.json`（レイアウト用途タグ・アンカー情報のカタログ）。
- 工程2の `layouts.jsonl`（利用可能なレイアウトカテゴリのヒント）。
- 制約情報（本編枚数上限、章テンプレ、付録方針）。
- 章テンプレ定義 (`config/chapter_templates/*.json`) と構成テンプレ適用ポリシー。
- Analyzer 連携データ（`analysis_summary.json` など工程5の集計結果）。
- 差戻し理由テンプレート辞書 (`return_reasons.json`)。

### 出力
- `draft_approved.json`: 章構成、スライド順、`layout_hint`、付録フラグ。
- `draft_draft.json`: AI 提案を含むドラフト案。
- `draft_review_log.json`: 章/スライド単位の承認・差戻し履歴。
- `draft_meta.json`: 章テンプレ適合率、Analyzer 指摘件数、差戻し理由コード別集計、付録統計など。
- 差戻しテンプレート辞書と Draft ログの紐付けメタ。

### ワークフロー
1. Draft API / CLI が章レーンとスライドカードの構成データを提示する。
2. AI が提案する構成案を基に、HITL が順序や章を調整する。
3. `layout_hint` を選択し、必要に応じて付録送りやスライド統合を行う。
4. 承認単位（章・スライド）で承認フラグを更新し、差戻し理由を記録する。
5. 承認完了後に `draft_approved.json` を出力し、同一工程内のマッピング処理へ渡す。

### 品質ゲート
- すべてのスライドが章に所属し、章順が定義されている。
- 工程3のストーリーフェーズ情報と章構成が整合している（不一致は差戻しまたは章調整を実施）。
- `layout_hint` が未設定のスライドが存在しない。
- 本編枚数が制約内に収まっている（超過は付録へ移動済み）。
- 承認ログが揃い、差戻し理由コードが必須項目として記録されている。

### ログ・連携
- 承認イベントログと工程3ログを `slide_uid` で突合可能にする。
- レイアウト候補スコア（用途タグ一致率、容量適合度、多様性）を記録する。
- 付録送り・統合の履歴を保持し、後続のマッピングで参照できるようにする。
- Analyzer 指摘サマリを章・スライド単位で保存し、差戻しテンプレートと相互参照できるようにする。
- 章テンプレ適用結果（適合率、過不足スライド）をメタ情報として保持する。

### RM-036 追加要件
- 章テンプレプリセット: `structure_pattern` ごとにテンプレ ID を定義し、Draft UI/CLI が章候補・過不足・適合率を表示する。`draft_*` には `chapter_template_id` と `template_match_score` を章単位で記録する。
- layout_hint インテリジェンス: Layout Hint Engine が候補ごとに `layout_score_detail`（用途タグ・容量・多様性・Analyzer 支援度）を算出し、CLI と Dashboard が理由を提示できるようにする。
- 差戻し理由テンプレート: 差戻し時に `return_reason_code` を必須化し、補足コメントを `return_reason_note` に分離する。コードはテンプレ辞書で管理し、ログで集計可能にする。
- Analyzer 連携: スライド単位の Analyzer 指摘件数を Draft ダッシュボードへ表示し、重大度順に差戻しテンプレート候補を優先表示する。`analyzer_summary` を Draft メタへ出力する。
- HITL UX: 章テンプレ・layout_hint 候補・差戻し理由コードを CLI / API から取得できるようインターフェースを拡張する。

### Analyzer サマリ連携要件
- 工程5（レンダリング）が生成する `analysis_summary.json` の形式を標準化（`severity_counts`, `layout_consistency`, `blocking_tags`, `last_analyzed_at` など）。
- Draft 工程は読み込み時にスライド ID の整合性チェックを行い、不一致があれば詳細エラーを返却する。
- analyzer_summary を差戻しテンプレ候補や layout_hint スコアに反映する。
- `analysis_summary.json` は 24 時間以内のデータを使用し、古いデータは再解析を促す。

### 未実装項目（4.1）
- 構成管理 API と `layout_hint` 管理機能の高度化。
- 多様性を考慮したレイアウト候補スコアリング。
- 付録送り・統合操作の履歴管理と再承認フロー。
- `story_outline` と `layout_hint` の自動整合チェック。
- 章テンプレ適用率の算出と `chapter_template_id` の読み書き。
- `layout_score_detail` と `analyzer_summary` を含む候補提示の整備。
- 差戻し理由コード辞書と Draft ログのテンプレ紐付け。

- `pptx outline` コマンドは承認済みコンテンツとレイアウト候補を入力に `draft_draft.json` / `draft_approved.json` / `draft_review_log.json` を生成し、章・スライド統計を `draft_meta.json` に出力する。
- `--content-approved` を指定した場合は工程3の成果物を再検証して Spec へ適用したうえで構成計算を実行する。未指定時は Spec を直接利用する。
- `--show-layout-reasons`, `--return-reasons`, `--import-analysis`, `--chapter-template` などのオプションで候補理由やテンプレ差戻し辞書を参照できる。
- `pptx compose` コマンドは `.pptx/extract/jobspec.json` を起点にドラフト承認とマッピングを連続実行し、`draft_*` と `generate_ready.json` / `mapping_log.json` を同時に更新する。

---

## 4.2 レイアウトマッピング（自動）

### 入力
- `draft_approved.json`: 章構成、スライド順、`layout_hint`。
- `content_approved.json`: テキスト・表・意図タグ。
- `jobspec.json`: レイアウト用途タグや推奨配置の基準情報。
- `layouts.jsonl`, `diagnostics.json`: レイアウト構造と警告情報。
- `branding.json`: ブランド設定とスタイル定義。
- 章テンプレ適用メタ（`draft_meta.json`）および差戻し履歴。

### 出力
- `generate_ready.json`: スライドごとの `layout_id`、プレースホルダ割付、`job_meta` / `job_auth` など。
- `mapping_log.json`: スコアリング結果、AI 補完箇所、フォールバック履歴、Analyzer 指摘サマリ。
- `fallback_report.json`: フォールバック発生時の対象スライドと理由一覧（任意）。

### ワークフロー
1. `layout_hint` と用途タグを基にレイアウト候補をフィルタし、スコアリングを実施する。
2. ルールベースで一次割付を行い、未配置要素を抽出する。
3. AI 補完で未割付や冗長要素を再配分し、必要に応じてスライド分割・縮約を行う。
4. フォールバックルール（縮約 → 分割 → 付録）を適用し、その履歴を記録する。
5. JSON スキーマ検証を通過した `generate_ready.json` を出力し、工程5へ送る。

### 品質ゲート
- 全スライドが `layout_id` を持ち、必須プレースホルダが埋まっている。
- `generate_ready.json` がスキーマ検証を通過し、空要素は意図的であるとログに記載されている。
- フォールバック適用時に理由が `mapping_log.json` に記録されている。
- Analyzer 指摘が `mapping_log.json` のメタおよびスライド単位サマリに反映され、後続工程で参照できる。
- AI 補完結果が監査ログで確認できる。

### ログ・監査
- 候補レイアウトのスコア（必須充足・容量適合・用途タグ・多様性）を保持する。
- AI 補完前後の差分を記録し、自動修正率を算出できるようにする。
- 収容不能ケースはエラー扱いとし、再実行のためのチェックリストを添付する。
- 監査ログ (`audit_log.json`) で `generate_ready`・`mapping_log` の SHA-256 を収集し、`mapping_meta` にスライド数・フォールバック対象 ID・生成時刻を記録する。

### 未実装項目（4.2）
- レイアウトスコアリングとフォールバック制御ロジック。
- AI 補完差分記録と監査ログ連携。
- `generate_ready.json` スキーマ検証ツールと失敗時ガイド生成。

### CLI 支援
- `pptx mapping` コマンドは `generate_ready.json`・`mapping_log.json`・必要に応じて `fallback_report.json` を生成する。
- `pptx compose` は工程4全体を通しで実行し、ドラフト成果物とマッピング成果物を同一フローで更新する。
- `mapping_log.json` と `draft_meta.json` は監査ログ・レポート生成系が参照できるよう共通形式を維持する。

---

## ロールバック方針
- 旧工程4/5 の構成に戻す場合は、本ファイルを復元し、`stage-05-mapping.md` を再導入する。
- CLI では `pptx outline`／`pptx mapping` の単独実行を維持しているため、工程統合によるオプション互換性を常時確認する。

## 参照ドキュメント
- `docs/design/stages/stage-04-mapping.md`
- `docs/design/schema/stage-04-mapping.md`
- `docs/runbooks/story-outline-ops.md`
- `docs/design/cli-command-reference.md`
