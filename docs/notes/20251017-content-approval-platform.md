# RM-023 ブリーフ承認プラットフォーム設計メモ（更新版）

## 背景
- 工程3 の HITL 承認基盤を `ContentSlide` から `BriefCard` へ移行するため、既存メモを刷新。
- `docs/design/stages/stage-03-content-normalization.md` と `docs/design/schema/stage-03-content-normalization.md` に合わせ、API / CLI / ストア構成を再整理した。

## コンポーネント構成
- **Brief Core Models**: `BriefCard`, `BriefStoryContext`, `BriefLogEntry`, `BriefAIRecord`。`brief_cards.json` / `brief_log.json` / `brief_ai_log.json` / `ai_generation_meta.json` で共通利用する。
- **BriefNormalizationStep**: パイプライン内で BriefCard 集合をロードし、工程4/5 へ `BriefDocument` と `BriefStoryOutline` を提供するステップ。
- **Review Log Aggregator**: `brief_log.json` を解析し、承認率・差戻し理由・Auto-fix 適用状況を集計する。
- **Integration Hooks**: Analyzer / Review Engine と連携し、AI 診断・Auto-fix 提案・禁則チェックをカード単位で記録する。
- **Audit Logger**: `audit_log.json` の `brief_normalization` セクションを生成し、入力ハッシュや成果物パス、承認統計を保持する。

## データモデル概要
- `BriefCard`: `card_id`, `chapter`, `message`, `narrative[]`, `supporting_points[]`, `story.phase`, `story.goal`, `intent_tags[]`, `status`, `autofix_applied[]`, `meta`.
- `BriefStoryContext`: 章テンプレ、ブランドトーン、必須メッセージ。CLI と API で共有。
- `BriefLogEntry`: `card_id`, `version`, `action`, `actor`, `timestamp`, `notes`, `applied_autofix[]`, `diff_snapshot`.
- `BriefAIRecord`: プロンプトテンプレ ID、モデル、トークン統計、レスポンスダイジェストを保持。

## パイプライン連携
- CLI `uv run pptx content samples/contents/sample_import_content_summary.txt` が BriefCard 生成の入口。`BriefAIOrchestrator` がカード下書きを作成し、`BriefStoreWriter` が `.pptx/content/` 配下へ保存する。
- `BriefNormalizationStep` が `PipelineContext` に `brief_document`, `brief_story_outline`, `brief_log`, `ai_generation_meta` を登録。工程4/5 は `BriefCard` 情報を直接参照する。
- Analyzer / Review Engine は BriefCard を入力に診断を実行し、結果をログおよびメタへ反映する。
- DAO / API 層は `BriefStore` を利用し、ETag 制御・監査ログ出力・差戻し履歴管理を提供する。

## テスト戦略
- モデル単体: `BriefCard` バリデーション（メッセージ長、証跡必須、ストーリー整合性）、Auto-fix JSON Patch の検証。
- CLI 統合: `samples/json/sample_brief.json` から `.pptx/content/` 成果物を生成し、JSON スナップショットで確認。警告やログ出力を assertion。
- API: `httpx` ベースで `/v1/brief/cards` 系エンドポイントをテストし、ETag と監査ログの整合をチェック。
- パイプライン: `BriefNormalizationStep` が `PipelineContext` に期待アーティファクトをセットすること、および `audit_log.json` の `brief_normalization` セクションが生成されることを確認。

## 課題・フォローアップ
- Auto-fix 適用履歴のハッシュ化、承認ログ署名。
- 複数ソース（Markdown, URL, CSV）をマージする際の証跡管理。
- BriefCard を扱う UI / Dashboard の設計と差戻しワークフローの可視化。
- RM-047 での Draft/Mapping 再設計とレイアウト推定ロジック刷新。
