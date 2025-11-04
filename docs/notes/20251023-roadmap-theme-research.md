# 2025-10-23 ロードマップ新テーマ検討

> 注記: 工程5の CLI は現在 `pptx gen` に統一済み。ここで言及する `pptx render` は検討当時の案です。

## 調査対象
- `docs/design/stages/` 各工程ドキュメント
- `docs/notes/2025-10-*` の設計・議事メモ
- `docs/requirements/requirements.md` および関連ストーリーファイル
- `docs/roadmap/roadmap.md` の現行テーマ・バックログ

## 候補テーマ一覧

### 1. テンプレートリリース監査強化
- 概要: テンプレ資産の差分検出・ゴールデンサンプル管理・LibreOffice/Polisher バージョン固定を体系化し、Analyzer 指標を Release レポートに取り込む。
- 根拠: テンプレ工程の未解決事項（`docs/design/stages/stage-01-template-preparation.md`）と Analyzer 活用メモの追加要件。
- 提案成果物: 差分アルゴリズム設計書、ゴールデンサンプル自動生成ガイド、LibreOffice/Polisher バージョン管理ポリシー、Analyzer 指標集計の runbook。
- 依存/前提: Analyzer 出力の集計仕様、テンプレ配布フローの既存スクリプト。
- 優先度メモ: 高（テンプレ更新ごとに手戻りリスクが高いため）。

### 2. branding.json 自動抽出 PoC
- 概要: PPTX テンプレートからフォント・配色・フッタ情報を抽出し `config/branding.json` と同期する CLI / スクリプトを実装する。
- 根拠: branding 設計メモ（`docs/notes/20251009-template-branding-config.md`, `docs/notes/20251011-branding-config-mapping.md`）。
- 提案成果物: 抽出スクリプト PoC、差分比較レポート、ブランド設定保守手順の更新。
- 依存/前提: python-pptx + XML 解析ユーティリティ、テンプレ代表サンプル。
- 優先度メモ: 中〜高（ブランド差異による不具合を抑止）。

### 3. SlideBullet グループ化移行計画
- 概要: 箇条書き要素をグループ単位でアンカー指定できるようスキーマを拡張し、旧形式から段階的に移行する。
- 根拠: 箇条書きアンカー課題メモ（`docs/notes/20251011-bullets-anchor-design-issue.md`）。
- 提案成果物: 新スキーマ設計、移行ガイド、互換テスト、警告ロジック。
- 依存/前提: `SlideBulletGroup` 実装、サンプル JSON 更新、Renderer/Analyzer のアンカー継承仕様。
- 優先度メモ: 中（技術的負債解消・複数アンカー対応の前提）。

### 4. Analyzer フィードバック基盤
- 概要: Analyzer 出力を各工程のメトリクス・UI・HITL ワークフローへ横断的に取り込む共通インターフェースを整備する。
- 根拠: アナライザー活用メモ（`docs/notes/20251016-pptx-analyzer-integration-opportunities.md`）と工程別未反映箇所。
- 提案成果物: 共通 API / ファイルスキーマ、工程別連携シナリオ、モニタリング連携 PoC。
- 依存/前提: `analysis.json` のバージョン管理、Monitoring Step 既存実装。
- 優先度メモ: 高（品質指標の社内共有と自動アラートに直結）。

### 5. HITL 承認 UX / オフライン運用整備
- 概要: CLI ベース承認の UX、欠損テーブル編集ハンドリング、Review Engine のスケーリング設計を固める。
- 根拠: 工程3 未解決事項（`docs/design/stages/stage-03-content-normalization.md`）と承認プラットフォーム設計メモ（`docs/notes/20251017-content-approval-platform.md`）。
- 提案成果物: オフライン承認フロー仕様、テーブル編集 UX ガイド、Review Engine ワーカー構成案。
- 依存/前提: Approval API/CLI、既存 Review Engine 実装。
- 優先度メモ: 中（HITL 運用の安定化が前提だが直ちに障害にはならない）。

### 6. ドラフト構成インテリジェンス拡張
- 概要: 章テンプレプリセット、AI layout hint 補助、差戻し理由テンプレートを組み込み構成調整の手戻りを削減。
- 根拠: 工程4 未解決事項（`docs/design/stages/stage-04-draft-structuring.md`）と Analyzer 連携の提案（`docs/notes/20251016-pptx-analyzer-integration-opportunities.md`）。
- 提案成果物: 章テンプレ管理モジュール、layout hint AI 補完 PoC、差戻し理由テンプレ集。
- 依存/前提: Layout Hint Engine、Analyzer メトリクス活用基盤。
- 優先度メモ: 中（HITL 効率化に寄与、他テーマの前提は少ない）。

### 7. マッピング AI 戦略とフィードバック
- 概要: AI 補完モデル選定・コスト試算、多様性指標拡張、フォールバック結果を HITL に返すワークフローを構築。
- 根拠: 工程4 未解決事項（`docs/design/stages/stage-04-mapping.md`）と Analyzer 連携案。
- 提案成果物: モデル比較レポート、スコアリング改善仕様、フォールバック通知 UI/CLI 設計。
- 依存/前提: AI 補完インターフェース、HITL ワークフロー、Monitoring ログ。
- 優先度メモ: 中（生成品質向上の余地が大きいが実装コストも高い）。

### 8. レンダリング観測性と互換性ガード
- 概要: Polisher 差分ログの標準化、LibreOffice バージョン互換検証、表画像化フォールバック・軽量整合チェック拡張を推進。
- 根拠: 工程5 未解決事項（`docs/design/stages/stage-05-rendering.md`）と Monitoring 統合メモ。
- 提案成果物: 差分ログスキーマ、バージョン互換テスト手順、表トラブル時のフォールバック設計。
- 依存/前提: Polisher 実行環境、Monitoring Step、Analyzer before/after 指標。
- 優先度メモ: 中〜高（本番事故防止に重要）。

### 9. パイプライン疎結合 CLI 再設計
- 概要: `pptx mapping` / `pptx render` の分離と `generate_ready` → `JobSpec` 変換ヘルパを整備し、再実行性と監査性を向上させる。
- 根拠: パイプライン疎結合化設計メモ（`docs/notes/20251018-pipeline-decoupling-design.md`）。
- 提案成果物: 新 CLI 実装、監査ログ更新、再実行手順書、移行ガイド。
- 依存/前提: 現行 CLI の互換要件、Mapping/Rendering Step のアーティファクト仕様。
- 優先度メモ: 高（工程ごとの再実行が現状困難なため）。

### 10. テンプレートパターン拡充
- 概要: `templates/templates.pptx` にブランド標準のページパターンを追加し、工程2・5・6 で生成可能なレイアウトの幅を広げる。
- 根拠: 新規要望（テンプレート拡充）、工程1/2 設計ドキュメント。
- 提案成果物: 追加レイアウトの設計ガイド、サンプル spec、レイアウト検証（layout-validate）ゴールデン更新。
- 依存/前提: テンプレ運用ポリシー、工程5の map スコアリング調整、Analyzer スナップショット更新。
- 優先度メモ: 中（生成バリエーション拡大の基盤）。

### 11. コンテンツ多形式インポート
- 概要: 工程3の入力を JSON に加えてテキスト・PDF・URL へ対応させ、サーバー側で取得・正規化するフローを整備する。
- 根拠: 新規要望（テキスト／PDF／URL 対応）、工程3 設計ドキュメント。
- 提案成果物: 変換パイプライン、フォーマットごとのバリデーション、取得ジョブ監査ログ。
- 依存/前提: Review Engine の前処理、認証・ネットワーク設定、セキュリティポリシー。
- 優先度メモ: 中（入力 UX 向上と運用リスク管理を両立する必要）。

### 12. コンテンツ生成AIオーケストレーション
- 概要: 工程3で生成AIを活用し、スライド候補生成ポリシーを外部から注入可能にする仕組みを整える。
- 根拠: 新規要望（ポリシー注入・AI整形）、`docs/design/stages/stage-03-content-normalization.md`。
- 提案成果物: ポリシー定義スキーマ、AI プロンプト管理、ヒューマンレビュー連携。
- 依存/前提: Review Engine / Content Service API、LLM 基盤、認可設定。
- 優先度メモ: 中〜高（提案／報告などユースケース差異に対応する鍵）。

### 13. レイアウト生成AI＋HITL ハイブリッド
- 概要: 工程4で生成AIが章立て・レイアウトを提案し、テキスト形式の可視化と自然言語指示による修正ループを提供する。
- 根拠: 新規要望（AI 章立て・可視化・自然言語指示）、`docs/design/stages/stage-04-draft-structuring.md`。
- 提案成果物: AI レイアウト提案 API、テキストサマリ出力、指示パースと差分適用、HITL UI/CLI 拡張。
- 依存/前提: Draft Service API、Layout Hint Engine、LLM 対話基盤。
- 優先度メモ: 高（HITL 工程の生産性向上効果が大きい）。

### 14. 情報ギャップインテリジェンス
- 概要: 工程3で生成AIが不足情報を検知し、ユーザーへのヒアリングや追加取得を支援する。
- 根拠: 新規要望（不足情報ヒアリング）、工程3 HITL の未解決事項。
- 提案成果物: ギャップ検出ルール、質問テンプレート、追記ログ、承認フローとの連携。
- 依存/前提: Content Service API、セキュアな問い合わせチャネル、LLM 推論基盤。
- 優先度メモ: 中（品質確保の観点で重要）。

### 15. 生成AI活用余地のリストアップ
- 概要: LLM/生成AI を他工程で活用できるポイントを継続的に棚卸しし、優先度を評価する。
- 根拠: 「生成AIに任せられるところはないか」要望。
- 提案成果物: AI 活用ロードマップ、評価指標、実験プロトコル。
- 依存/前提: 各工程の設計ドキュメント、LLM ガバナンス。
- 優先度メモ: 中（継続的な改善フレームが必要）。

## 補足メモ
- Analyzer 連携テーマ（候補4）は他候補の土台となるため、先行 PoC とロードマップ調整が必要。
- 既存バックログ（Service-F Distributor など）は今回の新規候補と競合するため、次回ロードマップ更新時に優先順位を再評価する。
- 各テーマの ToDo 化時は Approval-First Policy に従い、計画承認メッセージを記録すること。
