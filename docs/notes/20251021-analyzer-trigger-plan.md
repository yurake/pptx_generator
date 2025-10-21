---
title: RM-031 Analyzer 指摘に基づく補完トリガー計画
created: 2025-10-21
roadmap_item: RM-031 Analyzer マッピング補完連動
status: draft
---

## 背景
- `mapping_log.json` に Analyzer サマリ（件数集計・スライド別指摘）を出力できるようになった。
- Analyzer 指摘のうち `font_min`, `contrast_low`, `layout_consistency` などは補完／フォールバック制御と関連性が高い。
- 補完トリガーの優先度整理と自動シミュレーション手順を整備し、次フェーズでの AI 補完ルール改良につなげる必要がある。

## 目的
1. Analyzer 指摘からマッピング補完を起動する条件セットを定義する。
2. 条件に基づくシミュレーションをバッチ実行し、改善度とリスク指標を収集する。
3. 補完トリガーの採否判断と rollback 手順を runbook に落とし込む。

## 現状整理
- Analyzer 出力項目
  - `issue.type`: `font_min`, `contrast_low`, `bullet_depth`, `layout_consistency`, `margin`, `grid_misaligned` 等。
  - `metrics`: フォントサイズ、コントラスト比、段落レベル、グリッド逸脱、余白違反等。
- Mapping 側ログ
  - `slides[].analyzer.issue_counts_by_type` でスライド別件数を参照可能。
  - `meta.analyzer_issue_count` / `meta.analyzer_issue_counts_by_type` で全体集計を記録。
  - 既存フォールバック `shrink_text` / `fallback_report.json` は Analyzer 指摘を前提としていない。

## 追加で必要な作業
1. **トリガー定義ドラフト**
   - `font_min`: 既定 `min_font_size` 未満 → `MappingAIPatch` によるフォント引き上げ候補を生成。
   - `contrast_low`: `preferred_text_color` への置換案を補完候補へ追加。
   - `layout_consistency`: Bullet レベル調整を AI 補完前に優先適用し、再スコアリングを実施。
   - `margin` / `grid_misaligned`: 位置補正は工程6以降で処理するため、マッピング段階ではウォッチのみ。
2. **シミュレーション計画**
   - ゴールデンサンプルを用い、Analyzer 指摘→補完案→再レンダリング→再解析の流れをバッチ化。
   - 指標: 補完適用率、再発率（再解析後に同じ issue が残る割合）、生成時間の増分。
   - ツール: `uv run pptx gen` の `--emit-structure-snapshot` を併用し、修正前後の差分を比較。
3. **モニタリング設計**
   - `mapping_log.json` に補完トリガー実施履歴を追記（`ai_patch[].triggers` 等）するスキーマ拡張の検討。
   - `audit_log.json` へ Analyzer 指摘減少率を追加し、CI でグラフ化可能にする。
4. **運用更新**
   - Runbook（Analyzer・Support）にトリガー確認ステップおよび rollback 手順を追記。
   - ToDo／Issue テンプレートへ Analyzer 指摘の引用欄を追加し、補完結果の記録を統一。

## 次のアクション
1. トリガー定義案を設計資料に反映し、実装タスク（AI 補完拡張）へ切り出す。
2. シミュレーションのテストセットとスクリプト要件を `tests/AGENTS.md` に追記する。
3. Runbook・テンプレート更新の影響範囲を洗い出し、タスク管理ポリシーに沿って ToDo を発行する。

## メモ
- AI 補完の挙動によっては工程6 Analyzer の Fix と重複する可能性があるため、重複チェックと優先度ルールを設ける必要がある。
- 指摘件数がゼロでも補完が必要なケース（例: スタイル基準変更）を扱うため、トリガーは Analyzer 情報を優先指標としつつ、既存ヒューリスティックと組み合わせる。
