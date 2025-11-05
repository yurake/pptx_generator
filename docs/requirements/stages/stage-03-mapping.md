# 工程3 マッピング (HITL + 自動) 要件詳細

## 概要
- Brief 成果物をもとに章構成とレイアウト割付を連続的に実行し、`generate_ready.json` と `generate_ready_meta.json` を確定させる。
- HITL が章構成・差戻しを操作でき、フォールバックや Analyzer 結果を含む監査ログを `draft_review_log.json`・`mapping_log.json` に残す。
- CLI (`pptx compose` / `pptx outline`) と将来の UI から共通 API を利用できるよう、成果物構造とオプションを統一する。

## 入力
- Stage1: `jobspec.json`, `layouts.jsonl`, `branding.json`。
- Stage2: `prepare_card.json`, `brief_log.json`, `ai_generation_meta.json`。
- 章テンプレート辞書 `config/chapter_templates/*.json`。
- 差戻し理由辞書 `config/return_reasons.json`（任意）。
- （任意）`analysis_summary.json` など Analyzer 連携ファイル。

## 出力
- `generate_ready.json`: レイアウト割付済みの描画直前仕様。スライドごとに `layout_id`, `elements`, `meta.sources` を保持する。
- `generate_ready_meta.json`: 章テンプレ適合率、承認統計、Analyzer サマリ、AI 推薦採用件数、監査メタ情報を記録する。
- `draft_review_log.json`: 承認・差戻し履歴。`action`, `actor`, `timestamp`, `reason_code` を必須とする。
- `mapping_log.json`: レイアウト候補スコア、フォールバック履歴、AI 補完履歴、Analyzer 情報を記録する。
- `fallback_report.json`: 重大フォールバック（例: 章統合、付録送り）を詳細化した任意ファイル。

## 機能要件
1. **章構成管理（HITL）**
   - 章テンプレートの適合率を計算し、過不足章は `generate_ready_meta.template.mismatch[]` に出力する。
   - `layout_hint` 候補ごとにスコア (`layout_score_detail`) を算出。指標: 用途タグ一致度、容量適合度、多様性、Analyzer 支援度、テンプレ適合度。
   - 差戻し時は `return_reason_code` を必須化し、自由記述は `draft_review_log.json` の `notes` に記録する。
   - 承認完了後に章順・スライド順・付録情報を `generate_ready.json` に保存し、章ステータスを `generate_ready_meta.sections[*].status` へ反映。

2. **レイアウト割付（自動）**
   - BriefCard の intent / story_phase とテンプレ構造を突合し、最適レイアウトを選定する。
   - スコア上位候補から割付を試み、収容不可の場合は `shrink_text` → `split_slide` → `appendix` の順でフォールバック。
   - フォールバック結果と理由を `mapping_log.json.fallback` と `fallback_report.json` に記録する。
   - AI 補完（例: 箇条書き要約）を適用した場合は `mapping_log.json.ai_patch` に差分 ID・説明を残す。

3. **Analyzer 連携**
   - `analysis_summary.json` を `--analysis-summary` で読み込み、重大度に応じて候補スコアを補正する。
   - Analyzer 指摘サマリは `generate_ready_meta.sections[*].analyzer_summary` と `mapping_log.json.analyzer` に保存する。

4. **監査・再現性**
   - すべての成果物ファイルを監査ログに記録し、将来的に SHA256 ハッシュで突合できるようにする。
   - `pptx compose` / `pptx outline` / `pptx mapping` のいずれを用いても同じ成果物構成とログが得られること。
   - CLI は `--show-layout-reasons` オプションで候補理由を可視化し、CI / ダッシュボードでも確認できるよう JSON 出力を提供する。

## CLI 要件
- `pptx compose`
  - `--brief-*` オプションが未指定でも `.pptx/prepare/` の既定ファイルを自動参照する。
  - `--generate-ready-filename` / `--generate-ready-meta-filename` / `--review-log-filename` / `--mapping-log-filename` / `--fallback-report-filename` で成果物ファイル名を制御する。
  - 失敗時は exit code 2（スキーマ検証エラー）、4（ファイル読み込みエラー）、6（マッピング不可）を返す。
- `pptx outline`
  - `generate_ready` 系成果物のみ再生成する。`--refresh-candidates` 指定時は候補スコアも再計算する。

## 品質ゲート
- `generate_ready_meta.sections[*].status` に未承認 (`pending`) が残っていない。
- `generate_ready.json` のスライド数が `generate_ready_meta.statistics.cards_total` と一致する。
- `mapping_log.json` の `warnings` と `analyzer.issue_count` が監視対象（PagerDuty 等）へ連携可能な形式である。
- フォールバック発生時は `fallback_report.json` に詳細が記録され、HITL が差戻し判断を下せる。

## 将来計画 / 未解決事項
- Layout Hint Engine の ML 化と学習データパイプライン。
- 章テンプレート適合率のダッシュボード表示と KPI 化。
- Analyzer 指摘に応じた自動フォールバック戦略の改善。
- BriefCard と章テンプレの双方向同期（差分検出・再マッピングルール）。
