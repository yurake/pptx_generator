# 工程4 ドラフト構成設計 (HITL) 設計

## 目的
- 承認済みコンテンツを章立て・ページ順へ並べ、`layout_hint` を確定する。
- 付録送りや統合といった構成操作を Draft API / CLI で提供し、承認ログを監査可能にする。

## コンポーネント構成
| コンポーネント | 概要 | 技術 |
| --- | --- | --- |
| Draft Service API | 章/カード管理、layout_hint 候補計算 | FastAPI |
| CLI / Integration Scripts | Draft API を操作し、構成データを確認・更新 | Python |
| Layout Hint Engine | 工程2の `layouts.jsonl` を参照し候補提示 | Python |
| Draft Log Store | `draft_review_log.json` と履歴管理 | PostgreSQL / SQLite |
| Storyboard UI（バックログ） | 章レーン + スライドカードの視覚編集 | React / Next.js 等（検討中） |

## データモデル
- `chapter`: `chapter_id`, `title`, `order`, `status`
- `slide_card`: `slide_uid`, `chapter_id`, `order`, `layout_hint`, `layout_candidates[]`, `status`
- `draft_log`: `slide_uid`, `action`, `actor`, `timestamp`, `metadata`

## ワークフロー
1. `content_approved.json` から候補カードを生成し章レーンへ配置。  
2. Layout Hint Engine が用途タグと必須要素に基づき候補スコアを算出。  
3. ユーザーが CLI / 内製ツールから章・順序・付録を操作。  
4. layout_hint 決定 → 章単位で承認。  
5. 承認完了で `draft_approved.json` を書き出し、ログに記録。

## API エンドポイント例
- `GET /draft/board`：章・スライド一覧取得
- `POST /draft/slides/{slide_uid}/move`：章/順序更新
- `POST /draft/slides/{slide_uid}/hint`：layout_hint 選択
- `POST /draft/chapters/{chapter_id}/approve`：章承認
- `POST /draft/slides/{slide_uid}/appendix`：付録送り

## ルールエンジン
- スコアリング: 必須 PH (40%), 用途タグ一致 (30%), 容量適合 (20%), 多様性 (10%)
- 多様性: 同種レイアウト連続回避、セクション全文率などを計測。
- 付録処理: 本編枚数超過 or 低優先度タグで候補表示。

## エラーハンドリング
- 承認済み章の変更要求 → `409 Conflict`
- layout_hint 未選択で承認 → `400 Bad Request`
- 候補計算失敗時は fallback として工程2のデフォルトレイアウトを提示。

## 監視とロギング
- メトリクス: 承認リードタイム、章ごとの差戻し回数、付録移動数。
- ログ: layout_hint 選定理由、候補スコア一覧、章承認イベント。

## テスト戦略
- API 単体テスト: move/hint/approve のバリデーション。
- CLI / API シナリオテスト: 章入れ替え、付録移動、承認フローを一連で検証。
- 負荷: 大規模案件（50+ スライド）での操作レスポンスを計測。

## 未解決事項
- 章テンプレのプリセット管理方式。
- layout_hint 候補を AI 補完する場合の提示方法（将来 UI / 内製ツールで提供予定）。
- 差戻し理由テンプレート化の有無。

## 関連スキーマ
- [docs/design/schema/stage-04-draft-structuring.md](../schema/stage-04-draft-structuring.md)
- サンプル: [docs/design/schema/samples/draft_approved.jsonc](../schema/samples/draft_approved.jsonc)
