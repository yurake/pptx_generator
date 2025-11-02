# 2025-10-16 PPTX アナライザー活用アイデア整理

## 背景
- ブランチ `feat/pptx-analyzer` で実装された `SimpleAnalyzerStep` は、レンダリング済み PPTX を解析し `analysis.json` に品質指摘と修正案を記録する。
- Analyzer の出力を工程 1〜6 へどのように組み込めるか検討した結果を整理し、既存ドキュメントや計画への反映状況を確認する。
- 今回の検討では、各工程で「設計・要件にすでに記載されている内容」と「未反映だが有効な拡張案」を切り分けた。

## 工程別整理

### 工程1 テンプレ準備
- 既存ドキュメント  
  - `docs/design/stages/stage-01-template-preparation.md:11-21` で Golden Sample Runner がレンダリング→Analyzer→LibreOffice を通す想定を言及済み。
- 追加アイデア  
  - Analyzer 出力を release レポートへ集約し、テンプレ受け渡し時に指摘件数や種別の推移を追跡するメトリクス化。
  - 診断に落ちたテンプレ向けの修正手順を runbook 化し、制作チームへのフィードバックを定型化。
- 未反映領域  
  - 上記アイデアは requirements・design・roadmap いずれにも未掲載。新規タスクとして整理が必要。

### 工程2 テンプレ構造抽出
- 既存ドキュメント  
  - `docs/design/stages/stage-02-template-structure-extraction.md:37-40` に Analyzer/Renderer 連携インターフェースが未解決項目として記載。
- 追加アイデア  
  - 抽出したプレースホルダ情報と Analyzer のスナップショットを照合し、命名漏れやアンカー欠落を diff レポートで提示。
  - `diagnostics.json` へ Analyzer 由来の警告を取り込み、テンプレ構造の課題を一括で確認できるようにする。
- 未反映領域  
  - 要件・設計・ロードマップに具体的な行動計画は存在しない。RM-022 など関連タスクで扱う余地あり。

### 工程3 コンテンツ正規化 (HITL)
- 既存ドキュメント  
  - `docs/design/stages/stage-03-content-normalization.md` では Review Engine の診断と Auto-fix を中心に説明しているが、Analyzer 連携には触れていない。
- 追加アイデア  
  - `analysis.json` の `issues` / `fixes` を Review Engine が参照し、Auto-fix 提案やレビュー優先度の指標に利用。
  - `severity` に基づく差戻し優先度タグを UI に表示し、HITL レビューの効率化を図る。
- 2025-10-17 更新  
  - CLI で `review_engine_analyzer.json` を生成し、Analyzer 指摘を Review Engine 用の `AIReviewIssue` / `AutoFixProposal` に変換する処理を追加済み（未対応 Fix 種別は notes に記録）。
- 未反映領域  
  - 要件・設計・ロードマップでの記載なし。HITL 系ロードマップ項目（例: RM-024）への組み込みを検討。

### 工程4 ドラフト構成設計 (HITL)
- 既存ドキュメント  
  - `docs/design/stages/stage-04-draft-structuring.md` は章レーン UI と layout_hint 決定にフォーカスし、Analyzer の活用は未記載。
- 追加アイデア  
  - layout_hint 承認前に対象スライドの Analyzer 指摘件数をダッシュボードで可視化し、構成調整の判断材料とする。
  - `layout_consistency` の警告を Draft Service 側で再インデント候補に変換し、HITL 作業の手戻りを削減。
- 未反映領域  
  - ドキュメント・ロードマップともに未反映。工程 4 のワークフロー見直しタスクとして追加余地あり。

### 工程5 マッピング
- 既存ドキュメント  
  - `docs/design/stages/stage-04-mapping.md` ではスコアリングやフォールバック制御を定義。Analyzer 結果の活用は触れられていない。
- 追加アイデア  
  - `mapping_log.json` に Analyzer 警告を併記し、割付後も手当が必要な要素を可視化。
  - `font_min` や `contrast_low` を AI 補完トリガーとして利用し、補完対象の抽出を自動化。
- 未反映領域  
  - 必要な追加仕様は全て未記載。RM-025（マッピング補完エンジン）との連携検討が望ましい。

### 工程5 PPTX レンダリング
- 既存ドキュメント  
  - RM-013 でアナライザー実装が完了し、工程 6 後段で解析する方針はロードマップに記載済み（`docs/roadmap/roadmap.md:154-161`）。
  - `docs/design/stages/stage-06-rendering.md` は整合チェック・監査ログについて述べるが、Analyzer 結果との統合は未定。
- 追加アイデア  
  - レンダリング監査ログと `analysis.json` を突合し、CI やチャット通知で品質アラートを自動配信。
  - LibreOffice や Polisher 実行後に Analyzer を再走させ、修正の改善度合いを数値追跡。
- 未反映領域  
  - RM-026（レンダリング監査統合）には Analyzer 連携の詳細が含まれておらず、追加タスクとしての明文化が必要。

## 次のアクション候補
- 追加アイデアを工程別ロードマップ項目へ反映するためのタスク発行（例: RM-022, RM-024, RM-025, RM-026 の補強）。
- Analyzer 結果の共通インターフェース設計（API / CLI / ファイル連携）と、各工程での取り込みポイントを図式化した設計資料の作成。
- 通知・ダッシュボード系の PoC（メトリクス可視化、Slack/Teams 連携）で有効性を検証し、優先度を評価する。
