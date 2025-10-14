# 工程3 コンテンツ正規化 (HITL) 設計

## 目的
- 入力データをスライド素材に整形し、人の承認と AI レビューを統合する。
- 承認済みコンテンツを `content_approved.json` として後工程に渡す。

## システム構成
| レイヤ | コンポーネント | 概要 |
| --- | --- | --- |
| プレゼンテーション層 | Content Board UI | スライドカード表示、編集、承認操作 |
| サービス層 | Content Service API | コンテンツ CRUD、承認管理、ログ出力 |
| AI 補助 | Review Engine | LLM & ルールベースの診断と Auto-fix 提案 |
| ストレージ | Content Store | `content_draft.json`, `content_approved.json`, Review Logs |

## データモデル
- `content_card`: `slide_uid`, `title`, `body`, `bullets[]`, `tables[]`, `intent_tag`, `status`
- `review_log`: `slide_uid`, `action`, `actor`, `timestamp`, `notes`, `ai_grade`, `auto_fix_applied`
- `auto_fix_patch`: JSON Patch 互換形式で差分を表現

## ワークフロー
1. Input Processor が `spec.json` を分解しカードを生成。  
2. Review Engine が初期診断（A/B/C）と提案を付与。  
3. ユーザーが UI で修正、Auto-fix 適用、差戻し。  
4. `Approve` で `content_approved.json` へ反映しロック。  
5. 差戻しは `status=rework` として再生成対象に戻す。

## API 概要
- `POST /content/cards`: 初期カード作成
- `PATCH /content/cards/{slide_uid}`: 編集・Auto-fix 適用
- `POST /content/cards/{slide_uid}/approve`: 承認
- `POST /content/cards/{slide_uid}/return`: 差戻し
- `GET /content/logs`: 审査ログ出力

## AI レビュー連携
- ルール検証（禁則、数値、文字数）→ `critical` なら自動差戻し。
- LLM 評価はメッセージ構造化 (`grade`, `strengths`, `weaknesses`, `actions`) に揃える。
- Auto-fix は JSON Patch と自然文（説明）をセットで保存。

## エラーハンドリング
- 承認済みカードへの編集要求 → `409 Conflict`
- LLM エラー → 既存レビュー結果を保持しリトライフラグ付与
- 保存失敗 → Draft スナップショットからロールバック

## モニタリング
- メトリクス: 承認完了時間、Auto-fix 適用率、差戻し率、LLM 失敗率。
- ログ: UI 操作ログ、API アクセスログ、AI 呼び出しログを統合して監査。

## テスト戦略
- API 単体テスト（FastAPI 予定）、UI E2E（Playwright）。
- AI レビュー: 固定入力で determinism を確認、メトリクスのみ比較。

## 未解決事項
- オフライン承認（CLIベース）サポートの有無。
- 欠損テーブルのエディタ UX。
- Review Engine のスケール戦略（同期 vs 非同期処理）。

## 関連スキーマ
- [docs/design/schema/stage-03-content-normalization.md](../schema/stage-03-content-normalization.md)
- サンプル: [docs/design/schema/samples/content_approved.jsonc](../schema/samples/content_approved.jsonc)
