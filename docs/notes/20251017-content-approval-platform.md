# RM-023 コンテンツ承認プラットフォーム設計メモ（2025-10-17）

## 背景
- ロードマップ `RM-023 コンテンツ承認オーサリング基盤` に対応し、工程3の HITL 承認プロセスを実装するための土台を整理した。
- 既存 CLI は `JobSpec` を直接レンダリング工程へ渡しており、`content_approved.json` や承認ログの扱いが未定義の状態だった。
- `docs/design/schema/stage-03-content-normalization.md` と `docs/design/stages/stage-03-content-normalization.md` に記載された要件を満たすため、データモデル／パイプライン構成／テスト戦略を具体化した。

## コンポーネント構成案
- **Content Approval Core**: CLI／サービスが共通利用する Pydantic モデル群。`content_draft.json`／`content_approved.json`／`content_review_log.json` を型安全に扱えるようにする。
- **Approval Pipeline Step**: 既存パイプラインに `content_approved.json` をロードするステップを新設し、後工程が `PipelineContext` から承認済みデータを取得できるようにする。
- **Review Log Aggregator**: 承認ログ（`content_review_log.json`）を取り込み、監査・メトリクス用途の加工を行うクラスを別途準備する。第一段階はパーサと検証ロジックに留め、集計機能は後続タスクへ委譲。
- **Integration Hooks**: Analyzer／Refiner との連携を視野に入れ、適用済み Auto-fix 情報や禁止語チェック結果を `ContentSlide.applied_autofix` とログへ反映する。
- **Audit Logger**: `ContentApprovalStep` が生成するメタ情報（パス、スライド数、SHA256）を `audit_log.json` の `content_approval` / `content_review_log` セクションへ出力し、監査・再現トレースを支援する。

## データモデル設計
- `ContentElementBlock`: タイトル・本文・テーブル・ノートを保持。本文は 1 行 40 文字以内、最大 6 行までをバリデーション。
- `ContentTableData`: `headers` と `rows` の長さ整合性を検証し、セルは文字列へ正規化する。
- `JsonPatchOperation`: `op` / `path` / `value` / `from` を持つ JSON Patch 操作を表現。Auto-fix 提案に再利用する。
- `AutoFixProposal`: `patch_id` と説明文、複数の `JsonPatchOperation` から構成。
- `AIReviewIssue` / `AIReviewResult`: `grade` (`A`/`B`/`C`) と課題リスト、Auto-fix 提案の束を扱う。
- `ContentSlide`: `id` / `intent` / `type_hint` / `status`（`draft`/`approved`/`returned`）、`elements`、適用済み Auto-fix ID を保持。承認済みドキュメントでは `status=approved` を要求する。
- `ContentDocumentMeta`: `tone` / `audience` / `summary` など任意メタ情報。
- `ContentApprovalDocument`: `slides` と `meta` のトップレベルコンテナ。`content_draft.json` と `content_approved.json` の双方に共通利用する。
- `ContentReviewLogEntry`: `slide_id` / `action`（`approve`/`return`/`comment`）/`actor`/`timestamp` を ISO8601 で保持し、`applied_autofix` と `ai_grade` を任意で付随させる。

## パイプライン連携案
- CLI の `gen` コマンドで `--content-approved`（仮）を受け取り、存在する場合は `ContentApprovalDocument` を読み込み `PipelineContext` へ格納する。
- 新規 `ContentApprovalStep` を追加し、承認済みデータの有無を検証したうえでレンダリング前に `context.add_artifact("content_approved", document)` を実行する。
- Analyzer／Refiner は `content_approved` を参照し、承認済みテキストに対する追加チェックや Auto-fix 情報の集約を行えるよう拡張予定（本タスクではインターフェースのみ提供）。

## テスト戦略
- Pydantic モデルの単体テストでバリデーション（本文文字数・JSON Patch 正当性・承認ステータス）を検証する。
- CLI 統合テストでは `samples/json/sample_content_approved.json` を入力に追加し、パイプラインがアーティファクトを保持することを確認する。PDF 生成はスキップしてもよい。
- `samples/json/sample_content_approved.json` と `sample_content_review_log.json` を追加し、承認済みカード／レビュー履歴の標準ケースを提供する。
- 監査ログの `content_approval` は `applied_to_spec` と `updated_slide_ids` を保持し、`content_review_log` はアクション種別ごとの件数（`actions`）を集計する。
- 将来的に専用 UI を導入する際は、FastAPI レイヤの Schema と共通利用する想定。

## 課題・フォローアップ
- Auto-fix 適用履歴と承認ログのハッシュ検証は別タスクでの実装が必要。
- Review Engine とのリアルタイム連携（AI 呼び出し・非同期処理）は現フェーズの範囲外。
- 専用 UI 実装は後続フェーズで改めて検討する（当面は API／CLI 運用）。
