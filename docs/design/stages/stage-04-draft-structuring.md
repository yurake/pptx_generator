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
| Chapter Template Registry | `structure_pattern` ごとの章テンプレ管理と適合率計算 | Python (dataclass + JSON) |
| Draft Log Store | `draft_review_log.json` と履歴管理 | PostgreSQL / SQLite |
| Storyboard UI（バックログ） | 章レーン + スライドカードの視覚編集 | React / Next.js 等（検討中） |
| Analyzer Metrics Adapter | 工程6の `analysis_summary.json` を集約し Draft へ連携 | Python |
| Return Reason Template Store | 差戻し理由コード辞書の管理と CLI 提供 | JSON / YAML |

## データモデル
- `chapter`: `chapter_id`, `title`, `order`, `status`, `chapter_template_id`, `template_match_score`
- `slide_card`: `slide_uid`, `chapter_id`, `order`, `layout_hint`, `layout_candidates[]`, `layout_score_detail`, `analyzer_summary`, `status`
- `draft_log`: `slide_uid`, `action`, `actor`, `timestamp`, `return_reason_code`, `return_reason_note`, `metadata`
- `chapter_template`: `template_id`, `name`, `structure_pattern`, `required_sections[]`, `optional_sections[]`, `constraints`

## ワークフロー
1. `prepare_card.json` から候補カードを生成し章レーンへ配置。  
2. Chapter Template Registry が `structure_pattern` に合致する章テンプレを探し、章候補と不足・過剰を提示。  
3. Layout Hint Engine が用途タグ・容量・多様性・Analyzer 支援度をスコア化し候補提示。  
4. ユーザーが CLI / 内製ツールから章・順序・付録を操作し、差戻し時は理由コードを選択。  
5. layout_hint 決定 → 章単位で承認。Analyzer 指摘件数が閾値を超える場合は警告を表示。  
6. 承認完了で `draft_approved.json` と `draft_meta.json` を書き出し、ログに記録。

### 章テンプレプリセット
- `config/chapter_templates/*.json` にテンプレを定義（章名、順序、必須スライドタイプ）。
- Draft API はテンプレから `chapter_template_id` を割り当て、適合率と過不足スライドを算出する。
- CLI ではテンプレ一致率のランキングと、テンプレ未充足項目のチェックリストを出力する。
- テンプレ JSON のフィールド: `template_id`, `name`, `structure_pattern`, `required_sections[]`, `optional_sections[]`, `constraints`（章数・本編枚数など）。`constraints` は `max_main_pages`, `appendix_policy` を想定。
- バリデーション: `required_sections` が空の場合はエラー。`structure_pattern` は `draft_meta.json` の値と一致必須。`constraints.max_main_pages` 超過時は警告。
- 章テンプレ適合レポート: `draft_meta.json.template_mismatch[]` に不足・過剰章を列挙し、`severity`（`warn` / `blocker`）を併記。

### layout_hint インテリジェンス
- `layout_score_detail` は `uses_tag`, `content_capacity`, `diversity`, `analyzer_support` の 4 指標。
- `analyzer_support` は工程6の `analysis_summary` から重大度別件数を取得し、ヒント適合度を算出する。
- 候補提示時にスコア内訳を理由として表示し、HITL 作業者が提案妥当性を判断できるようにする。
- CLI 出力例:
  ```bash
  uv run pptx outline draft.json --show-layout-reasons
  ```
  ```
  Slide s08 layout_hint candidates:
    - overview (score 0.84)
      • uses_tag: +0.40 (matches business_overview)
      • content_capacity: +0.24 (fits 3 bullets)
      • diversity: +0.10 (avoids consecutive overview)
      • analyzer_support: +0.10 (no high severity issues)
    - comparison (score 0.66) ...
  ```
- API `GET /draft/slides/{slide_uid}/candidates` で `layout_score_detail` を返却し、UI や CLI が詳細説明を共有可能にする。

### 差戻し理由テンプレート
- `return_reason_code` は章・スライド共通のコード体系（例: `STRUCTURE_GAP`, `ANALYZER_BLOCKER`）。
- CLI はコード一覧と推奨コメント例を提示し、再発防止メモを `return_reason_note` に蓄積する。
- Analyzer 指摘が重大度 High の場合、対応する差戻しコードを優先表示する。
- テンプレ辞書 (`return_reasons.json`) フィールド: `code`, `label`, `description`, `severity`, `default_actions[]`, `related_analyzer_tags[]`。
- 差戻し記録時の UX: CLI は `--return-reason STRUCTURE_GAP --note "補強が必要"` の形式で受け付け、未指定時はエラー。

### Analyzer サマリ連携
- 工程6は `analysis_summary.json` を生成し、スライド単位に `severity_counts`, `layout_consistency`, `blocking_tags[]` を記録する。
- Draft サービスは `analysis_summary.json` を `draft_meta.json.analyzer_summary` へ統合し、候補提示と差戻しテンプレ選択のトリガに使用する。
- CLI では `--show-analyzer` オプションで章/スライドの重大度合計とブロッキング要因を一覧表示する。

### CLI / API インターフェース拡張
- CLI 追加オプション
  - `--chapter-template <template_id>`: 強制的にテンプレを指定し、適合度を再計算。
  - `--return-reasons`: 差戻しテンプレ一覧を表示。
  - `--show-layout-reasons`: layout_hint 候補のスコア内訳を表示（デフォルト OFF）。
  - `--import-analysis <path>`: 工程6で生成した `analysis_summary.json` を読み込み、`analyzer_support` を再計算。
- API 追加エンドポイント
  - `GET /draft/templates`: テンプレ辞書を一覧返却。クエリ `structure_pattern` で絞り込み。
  - `GET /draft/return-reasons`: 差戻し理由テンプレ一覧を返却。
  - `POST /draft/analyzer/import`: `analysis_summary.json` をアップロードし、`analyzer_summary` を更新。
  - 既存エンドポイントのレスポンスに `layout_score_detail`, `chapter_template_id`, `template_match_score`, `analyzer_summary` を含める。

## API エンドポイント例
- `GET /draft/board`：章・スライド一覧取得
- `GET /draft/templates`：章テンプレ辞書取得
- `POST /draft/slides/{slide_uid}/move`：章/順序更新
- `POST /draft/slides/{slide_uid}/hint`：layout_hint 選択
- `POST /draft/chapters/{chapter_id}/approve`：章承認
- `POST /draft/slides/{slide_uid}/appendix`：付録送り
- `POST /draft/analyzer/import`：Analyzer サマリ登録

## ルールエンジン
- スコアリング: 必須 PH (40%), 用途タグ一致 (30%), 容量適合 (20%), 多様性 (10%)
- 多様性: 同種レイアウト連続回避、セクション全文率などを計測。
- 付録処理: 本編枚数超過 or 低優先度タグで候補表示。
- Analyzer 連携: `analyzer_support` では重大度別件数と `layout_consistency` を参照し、スコア減点または改善アクションを提案。
- 章テンプレ一致: `template_match_score` が閾値以下の場合は警告を表示し、テンプレ補完候補を提示。
- 差戻し理由テンプレ: ブロッキング要因が存在する場合、`severity=blocker` のコードをデフォルト選択。`return_reasons.json.related_analyzer_tags` を活用して候補順をソート。
- CLI `--preflight` では章テンプレ適合・Analyzer ブロッカー・差戻しテンプレ必須項目を一括チェックする。

## エラーハンドリング
- 承認済み章の変更要求 → `409 Conflict`
- layout_hint 未選択で承認 → `400 Bad Request`
- 候補計算失敗時は fallback として工程2のデフォルトレイアウトを提示。
- 差戻し理由コード未指定 → `422 Unprocessable Entity`
- Analyzer 指摘駆動の警告を無視して承認 → ログへ `acknowledged_analyzer_risk=true` を記録。
- `analysis_summary.json` のスライド ID 不一致 → `400 Bad Request` とし、詳細な不一致リストを返却。
- 登録済みテンプレ ID 以外を `--chapter-template` で指定 → `404 Not Found`。

## 監視とロギング
- メトリクス: 承認リードタイム、章ごとの差戻し回数、付録移動数。
- 追加メトリクス: 章テンプレ適合率、差戻し理由コード別件数、Analyzer 重大度別未処理件数。
- ログ: layout_hint 選定理由、候補スコア一覧、章承認イベント、テンプレ一致診断、Analyzer 警告受領履歴。
- ログ例 (`draft_log` 拡張): `{"action":"return","return_reason_code":"ANALYZER_BLOCKER","related_analyzer_tags":["layout_consistency"],"template_match_score":0.65}`
- メトリクスエクスポータ: Prometheus で `draft_template_match_score`、`draft_return_reason_count{code=...}`、`draft_analyzer_blockers_total` を収集。

## テスト戦略
- API 単体テスト: move/hint/approve のバリデーション。
- CLI / API シナリオテスト: 章入れ替え、付録移動、承認フローを一連で検証。
- 負荷: 大規模案件（50+ スライド）での操作レスポンスを計測。
- TM PoC テスト: 章テンプレ適合率計算、差戻し理由コード選択 UX、Analyzer 指標の閾値判定。
- Analyzer インポートテスト: `analysis_summary.json` の欠落・ID 不一致・重大度閾値の挙動検証。
- CLI オプションテスト: `--show-layout-reasons`, `--return-reasons`, `--import-analysis` の出力整合性確認。

## 未解決事項
- 章テンプレプリセットのライフサイクル管理と更新フロー。
- layout_hint 候補の AI 補完アルゴリズム（閾値調整、学習データ）と UI 連携。
- 差戻しテンプレートのコード体系拡張と運用部門の合意形成。
- Analyzer 指標のリアルタイム化（工程6からの連携頻度、キャッシュ戦略）。
- 章テンプレと差戻しテンプレの翻訳・多言語対応。
- Analyzer サマリの差分更新（フル replace ではなく patch）をどう扱うか。

## 関連スキーマ
- [docs/design/schema/stage-04-draft-structuring.md](../schema/stage-04-draft-structuring.md)
- サンプル: [docs/design/schema/samples/draft_approved.jsonc](../schema/samples/draft_approved.jsonc)

- CLI: `uv run pptx outline spec.json --brief-cards .pptx/prepare/prepare_card.json --show-layout-reasons --chapter-template bp-report-2025`
- CLI: `uv run pptx outline spec.json --brief-cards .pptx/prepare/prepare_card.json --brief-log .pptx/prepare/brief_log.json --layouts layouts.jsonl --chapter-template bp-report-2025 --show-layout-reasons`
