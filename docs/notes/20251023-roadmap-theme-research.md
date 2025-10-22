# 2025-10-23 ロードマップ新テーマ検討

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
- 根拠: 工程5 未解決事項（`docs/design/stages/stage-05-mapping.md`）と Analyzer 連携案。
- 提案成果物: モデル比較レポート、スコアリング改善仕様、フォールバック通知 UI/CLI 設計。
- 依存/前提: AI 補完インターフェース、HITL ワークフロー、Monitoring ログ。
- 優先度メモ: 中（生成品質向上の余地が大きいが実装コストも高い）。

### 8. レンダリング観測性と互換性ガード
- 概要: Polisher 差分ログの標準化、LibreOffice バージョン互換検証、表画像化フォールバック・軽量整合チェック拡張を推進。
- 根拠: 工程6 未解決事項（`docs/design/stages/stage-06-rendering.md`）と Monitoring 統合メモ。
- 提案成果物: 差分ログスキーマ、バージョン互換テスト手順、表トラブル時のフォールバック設計。
- 依存/前提: Polisher 実行環境、Monitoring Step、Analyzer before/after 指標。
- 優先度メモ: 中〜高（本番事故防止に重要）。

### 9. パイプライン疎結合 CLI 再設計
- 概要: `pptx mapping` / `pptx render` の分離と `rendering_ready` → `JobSpec` 変換ヘルパを整備し、再実行性と監査性を向上させる。
- 根拠: パイプライン疎結合化設計メモ（`docs/notes/20251018-pipeline-decoupling-design.md`）。
- 提案成果物: 新 CLI 実装、監査ログ更新、再実行手順書、移行ガイド。
- 依存/前提: 現行 CLI の互換要件、Mapping/Rendering Step のアーティファクト仕様。
- 優先度メモ: 高（工程ごとの再実行が現状困難なため）。

## 補足メモ
- Analyzer 連携テーマ（候補4）は他候補の土台となるため、先行 PoC とロードマップ調整が必要。
- 既存バックログ（Service-F Distributor など）は今回の新規候補と競合するため、次回ロードマップ更新時に優先順位を再評価する。
- 各テーマの ToDo 化時は Approval-First Policy に従い、計画承認メッセージを記録すること。
