# RM-023 プレペア承認プラットフォーム設計メモ（更新版）

## 背景
- stage 3 の HITL 承認基盤を `ContentSlide` から `PrepareCard` へ移行するため、既存メモを刷新。
- `docs/design/stages/stage-03-content-normalization.md` と `docs/design/schema/stage-03-content-normalization.md` に合わせ、API / CLI / ストア構成を再整理した。

## コンポーネント構成
- **Prepare Core Models**: `PrepareCard`, `PrepareStoryContext`, `PrepareLogEntry`, `PrepareAIRecord`。`prepare_card.json` / `prepare_log.json` / `prepare_ai_log.json` / `ai_generation_meta.json` で共通利用する。
- **PrepareNormalizationStep**: パイプライン内で PrepareCard 集合をロードし、stage 4/5 へ `PrepareDocument` と `PrepareStoryOutline` を提供するステップ。
- **Review Log Aggregator**: `prepare_log.json` を解析し、承認率・差戻し理由・Auto-fix 適用状況を集計する。
- **Integration Hooks**: Analyzer / Review Engine と連携し、AI 診断・Auto-fix 提案・禁則チェックをカード単位で記録する。
- **Audit Logger**: `audit_log.json` の `prepare_normalization` セクションを生成し、入力ハッシュや成果物パス、承認統計を保持する。

## データモデル概要
- `PrepareCard`: `card_id`, `order`, `role.story_phase`, `role.intent_tags`, `content.title`, `content.headline`, `content.body[]`, `content.notes[]`, `meta`（Blueprint 参照や生成時刻などを格納）。
- `PrepareStoryContext`: 章テンプレ、ブランドトーン、必須メッセージ。CLI と API で共有。
- `PrepareLogEntry`: `card_id`, `version`, `action`, `actor`, `timestamp`, `notes`, `applied_autofix[]`, `diff_snapshot`.
- `PrepareAIRecord`: プロンプトテンプレ ID、モデル、トークン統計、レスポンスダイジェストを保持。

## パイプライン連携
- CLI `uv run pptx prepare samples/contents/sample_import_content_summary.txt` が PrepareCard 生成の入口。`PrepareAIOrchestrator` がカード下書きを作成し、`PrepareStoreWriter` が `.pptx/prepare/` 配下へ保存する。
- `PrepareNormalizationStep` が `PipelineContext` に `prepare_document`, `prepare_story_outline`, `prepare_log`, `ai_generation_meta` を登録。stage 4/5 は `PrepareCard` 情報を直接参照する。
- Analyzer / Review Engine は PrepareCard を入力に診断を実行し、結果をログおよびメタへ反映する。
- DAO / API 層は `PrepareStore` を利用し、ETag 制御・監査ログ出力・差戻し履歴管理を提供する。

## テスト戦略
- モデル単体: `PrepareCard` バリデーション（メッセージ長、証跡必須、ストーリー整合性）、Auto-fix JSON Patch の検証。
- CLI 統合: `samples/contents/sample_import_content_summary.txt` から `.pptx/prepare/` 成果物を生成し、JSON スナップショットで確認。警告やログ出力を assertion。
- API: `httpx` ベースで `/v1/prepare/cards` 系エンドポイントをテストし、ETag と監査ログの整合をチェック。
- パイプライン: `PrepareNormalizationStep` が `PipelineContext` に期待アーティファクトをセットすること、および `audit_log.json` の `prepare_normalization` セクションが生成されることを確認。

## 課題・フォローアップ
- Auto-fix 適用履歴のハッシュ化、承認ログ署名。
- 複数ソース（Markdown, URL, CSV）をマージする際の証跡管理。
- PrepareCard を扱う UI / Dashboard の設計と差戻しワークフローの可視化。
- RM-047 での Draft/Mapping 再設計とレイアウト推定ロジック刷新。
