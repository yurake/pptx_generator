# 工程4 マッピング (HITL + 自動) 設計

## 目的
- 承認済みコンテンツを章構成へ落とし込み、テンプレ構造に合致した `rendering_ready.json` を生成するまでを一体として扱う。
- HITL によるドラフト調整と自動マッピングを一貫したアーキテクチャで提供し、監査可能なログとメタ情報を残す。

## コンポーネント構成
| コンポーネント | 役割 | 技術 | メモ |
| --- | --- | --- | --- |
| Draft Service API | 章/スライド管理、差戻し・承認ワークフロー | FastAPI | `draft_*` と差戻しログを生成。 |
| Layout Hint Engine | 工程2の `layouts.jsonl` を参照し候補提示・スコア計算 | Python | `layout_score_detail` を算出し CLI / UI に理由を提示。 |
| Chapter Template Registry | `structure_pattern` ごとの章テンプレ適用 | Python (dataclass + JSON) | 適合率と過不足章を計算し `draft_meta.json` に出力。 |
| Draft Log Store | `draft_review_log.json` や差戻し履歴管理 | PostgreSQL / SQLite | CLI は JSON 書き出しを提供。 |
| Mapping Engine | `rendering_ready.json` の生成、フォールバック制御 | Python | ルールベース＋AI 補完でプレースホルダ割付を完了。 |
| Fallback Handler | 縮約・分割・付録送りの制御とログ化 | Python | `mapping_log.json` / `fallback_report.json` に履歴を残す。 |
| Analyzer Metrics Adapter | 工程5（レンダリング）からの `analysis_summary.json` をドラフトへ連携 | Python | `analyzer_summary` をスライド単位で同期。 |
| CLI (`pptx outline` / `pptx mapping` / `pptx compose`) | HITL 作業・自動実行の統合インターフェース | Python / Click | compose で工程4全体を一括実行。 |

## サブ工程構成
- **4.1 ドラフト構成（HITL）**: 章構成・`layout_hint` の確定、差戻し理由管理、テンプレ適合率計測。
- **4.2 レイアウトマッピング（自動）**: レイアウト候補スコアリング、プレースホルダ割付、フォールバック・AI 補完、`rendering_ready.json` 生成。

---

## 4.1 ドラフト構成（HITL）

### データモデル
- `chapter`: `chapter_id`, `title`, `order`, `status`, `chapter_template_id`, `template_match_score`。
- `slide_card`: `slide_uid`, `chapter_id`, `order`, `layout_hint`, `layout_candidates[]`, `layout_score_detail`, `analyzer_summary`, `status`。
- `draft_log`: `slide_uid`, `action`, `actor`, `timestamp`, `return_reason_code`, `return_reason_note`, `metadata`。
- `chapter_template`: `template_id`, `name`, `structure_pattern`, `required_sections[]`, `optional_sections[]`, `constraints`。

### フロー
1. `content_approved.json` と `jobspec.json` を読み込みカードを生成。Chapter Template Registry が候補テンプレを提示。  
2. Layout Hint Engine が用途タグ・容量・多様性・Analyzer 支援度をスコア化し候補提示。  
3. HITL が CLI / UI で章順・付録・差戻しを更新。`return_reason_code` はテンプレ辞書から選択。  
4. layout_hint 決定後に章単位で承認。Analyzer 指摘件数が閾値を超えた場合は警告を表示。  
5. 承認完了時に `draft_approved.json` / `draft_meta.json` / `draft_review_log.json` を保存し、4.2 へハンドオフ。

### 章テンプレプリセット
- `config/chapter_templates/*.json` にテンプレ構造（必須章、章順、上限枚数）を定義。  
- Draft API はテンプレから `chapter_template_id` を割り当て、適合率と過不足章を計算。  
- `draft_meta.json.template_mismatch[]` に不足・過剰章を列挙し、`severity` を併記。  
- CLI はテンプレ一致率ランキングと未充足チェックリストを出力。

### layout_hint インテリジェンス
- `layout_score_detail` は `uses_tag`, `content_capacity`, `diversity`, `analyzer_support` の 4 指標。  
- CLI `--show-layout-reasons` で候補理由を視覚化。API `/draft/slides/{id}/candidates` で同情報を返却。  
- Analyzer の重大度と差戻しテンプレを連携し、警告を優先表示。

### 差戻し理由テンプレート
- `return_reasons.json` を辞書として管理（`code`, `label`, `description`, `severity`, `related_analyzer_tags[]` など）。  
- CLI は `--return-reasons` で一覧表示、`--return-reason <code>` オプションで差戻し登録。  
- 差戻しログは `draft_review_log.json` に追記し、監査ログと突合可能にする。

### Analyzer 連携
- 工程5が生成する `analysis_summary.json` を取り込み、スライド単位の `analyzer_summary` を更新。  
- 前回解析から 24 時間以上経過した場合は再解析を促す。  
- 差戻しテンプレ候補や layout_hint スコア計算に Analyzer 情報を活用する。

### 未実装・課題
- 多様性を考慮したスコアリングアルゴリズムの高度化。  
- 付録送り・統合操作の履歴管理と再承認フロー。  
- `story_outline` との自動突合。  
- 章テンプレと差戻しテンプレの翻訳対応。  
- Analyzer サマリの差分更新方式。

### CLI / API
- `uv run pptx outline ...` がドラフト工程の標準実装。`--show-layout-reasons` / `--import-analysis` / `--chapter-template` 等で追加情報を制御。  
- API: `POST /draft/chapters`, `PATCH /draft/slides/{id}`, `POST /draft/slides/{id}/approve`, `POST /draft/slides/{id}/return` などを提供予定。

---

## 4.2 レイアウトマッピング（自動）

### アーキテクチャ
- Mapping Engine は Draft 成果物とテンプレ構造を統合し、`rendering_ready.json` を生成する。  
- ルールベース割付 → AI 補完 → フォールバック制御の 3 レイヤ構成。  
- 監査・可観測性のため `mapping_log.json`, `fallback_report.json` を同時に出力。

### 主要処理
1. 候補レイアウト生成: `layout_hint` と `jobspec.json` に記載された用途タグで候補を絞り、スコアリングする。  
2. ルールベース割付: 必須プレースホルダの充足、オーバーフロー検知、推奨図表の配置。  
3. AI 補完: 未割付要素や過剰要素を再配分し、必要時はスライド分割・縮約。  
4. フォールバック: 縮約 → 分割 → 付録送り の順で適用し、履歴をログ化。  
5. 検証・出力: JSON スキーマ検証を通過後、`rendering_ready.json` と監査ログを保存。

### ログ設計
- `mapping_log.json`: 候補スコア、AI 補完差分、フォールバック履歴、Analyzer サマリを集約。  
- `fallback_report.json`: フォールバック発生時の対象スライドと理由一覧。  
- 監査ログ (`audit_log.json`) に `rendering_ready`・`mapping_log` の SHA-256 を記録し、時刻・スライド数・フォールバック件数を格納。  
- `mapping_meta` にはスライド数、フォールバック対象 ID、AI 補完ステータスを含める。

### 品質ゲート
- 全スライドに `layout_id` を付与し、必須プレースホルダが埋まっている。  
- `rendering_ready.json` がスキーマ検証を通過し、空要素には理由が紐付く。  
- フォールバック理由が `mapping_log.json` に記録され、工程5で追跡可能。  
- Analyzer 指摘件数がメタに反映され、重大度に応じたハイライトが行われる。  
- AI 補完箇所が追跡可能で、監査ログで確認できる。

### 未実装・課題
- レイアウトスコアリングとフォールバック制御ロジックの最適化。  
- AI 補完差分記録と監査ログ連携。  
- `rendering_ready.json` スキーマ検証ツールと失敗時ガイド生成。  
- Analyzer とのループ連携強化（工程5での再解析結果を再取り込み）。

### CLI / API
- `uv run pptx mapping ...` が標準実装。`pptx compose` は工程4全体を連続実行する。  
- API（バックログ）: `POST /mapping/run`, `GET /mapping/result/{spec_id}`, `GET /mapping/logs/{spec_id}` などを想定。

---

## 参照スキーマ
- [docs/design/schema/stage-04-mapping.md](../schema/stage-04-mapping.md)
- サンプル: `rendering_ready.jsonc`, `mapping_log.jsonc`, `draft_approved.jsonc`

## 関連ドキュメント
- `docs/runbooks/story-outline-ops.md`
- `docs/design/cli-command-reference.md`
- `docs/requirements/stages/stage-04-mapping.md`

## ロールバック方針
- 旧工程4/5 分割構成へ戻す場合は、本ファイルを復元し、`stage-04-draft-structuring.md` と `stage-05-mapping.md` を再配置する。  
- CLI の `pptx outline` / `pptx mapping` は継続提供しているため、統合後もオプション互換性の回帰確認を行う。
