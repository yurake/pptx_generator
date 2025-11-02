# 2025-10-23 RM-036 ドラフト構成インテリジェンス調査メモ

## 背景
- RM-036 のゴールに沿い、章テンプレ・layout_hint 候補提示・差戻し理由テンプレートを体系化して HITL 工程の手戻りを削減する方針を整理した。
- 現状仕様は `docs/design/stages/stage-04-draft-structuring.md` と `docs/requirements/stages/stage-04-draft-structuring.md` に集約されているが、テンプレ運用や Analyzer 連携は未定義のままである。
- Analyzer 活用案（`docs/notes/20251016-pptx-analyzer-integration-opportunities.md`）との整合、および Stage 4 の未解決事項の棚卸しを本メモで実施した。

## 現状整理
### 章テンプレ運用
- 現行ドキュメントでは章テンプレの具体的な管理手段がなく、工程3で得た `story.phase` 情報とヒューリスティクスで章順を決定している。
- `draft_draft.json` の `meta.structure_pattern` は存在するが、テンプレ定義や評価指標が不明瞭。

### layout_hint 候補提示
- Layout Hint Engine は用途タグ・容量・多様性をスコア化する想定だが、スコア内訳や根拠保存が仕様化されていない。
- 候補提示は CLI 出力のみに限定され、HITL 補助への転用方針がない。

### 差戻し理由テンプレート
- 差戻し時の理由は自由記述で、章テンプレや Analyzer 指摘との紐付けがなく再利用性が低い。
- 同種の差戻しが繰り返されている場合も個別メモに留まり、集計ができない。

### Analyzer 指標活用
- Analyzer の `layout_consistency` や `issues` 件数を構成判断に利用する計画が未記述。
- Draft ダッシュボードや CLI へ提示する際の整形フォーマットが定義されていない。

## 課題
- 章テンプレが定義されていないため、案件種別による標準構成の差分管理ができていない。
- layout_hint 候補の裏付けが可視化されず、HITL 作業者が AI 提案へ十分な信頼を置けない。
- 差戻し理由が標準化されておらず、再発防止策やノウハウ蓄積につながらない。
- Analyzer 指標を工程4へ持ち込む導線がなく、構成判断の優先度付けが属人的。

## PoC ターゲット案
- 章テンプレプリセット PoC: `config/chapter_templates/*.json` にテンプレ構造を定義し、Draft API が `structure_pattern` と照合して章候補とギャップを提示する。評価指標はテンプレ一致率と差戻し減少率。
- layout_hint インテリジェンス PoC: Layout Hint Engine が `score_breakdown` を計算し、用途タグ一致・容量適合・多様性・Analyzer 警告対応度を JSON で保存。CLI / Dashboard で候補理由を説明可能にする。
- 差戻し理由テンプレート PoC: 差戻し入力を `return_reason_code` + 補足コメントに分離し、章テンプレ・Analyzer 指摘と相互参照できるようログスキーマを調整する。

## データ項目案
- `chapter_template_id`: 章テンプレ適用を追跡。`draft_*` ファイルの章単位メタ情報に追加。
- `layout_score_detail`: layout_hint 候補ごとの内訳。`uses_tag`, `content_capacity`, `diversity`, `analyzer_support` などを含む。
- `analyzer_summary`: スライドごとの重大度別件数を保持し、差戻しテンプレートから参照。
- `return_reason_code`: 差戻し理由の定型コード。自由記述は `return_reason_note` へ分離。

## リスクと前提
- 章テンプレは案件ごとに差異が大きく、テンプレ粒度を誤ると適合率が低下する。
- Analyzer 連携は工程5の出力形式に依存するため、メトリクスの時点同期が課題。
- 差戻しテンプレートの導入には HITL 運用チームとの合意形成が必要で、運用変更の影響が大きい。

## 次アクション
- Stage 4 要件・設計ドキュメントへ上記データ項目と PoC スコープを追記する。
- Draft スキーマに `chapter_template_id` と `layout_score_detail` を追加し、差戻しログのテンプレコード化を定義する。
- ロードマップ RM-036 のステータスを調査中へ更新し、以降の実装タスク分解案を ToDo に反映する。
- Analyzer 指標の集計フローを工程5担当と擦り合わせるタスクを別途起案する。

## 詳細仕様補足（2025-10-23）
- 章テンプレ辞書 (`config/chapter_templates/*.json`)
  - フォルダ階層は `structure_pattern` 単位を推奨 (`config/chapter_templates/report/bp-report-2025.json` 等)。
  - フィールド: `template_id`, `name`, `structure_pattern`, `required_sections[]`, `optional_sections[]`, `constraints`.
  - `constraints` は `max_main_pages`, `appendix_policy`, `tags[]` を想定。`appendix_policy` は `overflow|allow|block`。
  - 適合レポート: `draft_meta.template_mismatch[]` で不足章や超過章を特定し、`severity` を `warn/blocker` で記録する。
- 差戻し理由テンプレ (`return_reasons.json`)
  - 配列形式で管理し、`code`, `label`, `description`, `severity`, `default_actions[]`, `related_analyzer_tags[]` を保持。
  - CLI は `uv run pptx outline ... --return-reasons` で一覧表示、差戻し操作では `--return-reason <code>` を必須化。
- Analyzer サマリ (`analysis_summary.json`)
  - 工程5がスライド単位で出力。`severity_counts`, `layout_consistency`, `blocking_tags`, `last_analyzed_at` を含む。
  - Draft 工程取り込み時にスライド ID が未一致であれば詳細エラーを返す。
- CLI / API 追加仕様
  - 新オプション: `--show-layout-reasons`, `--chapter-template`, `--import-analysis`, `--return-reasons`.
  - 新 API: `GET /draft/templates`, `GET /draft/return-reasons`, `POST /draft/analyzer/import`。
  - 既存レスポンスに `layout_score_detail`, `chapter_template_id`, `template_match_score`, `analyzer_summary` を追加。
- テスト観点
  - Analyzer インポート検証（欠落 or 不一致）、差戻しテンプレ必須化、章テンプレ強制指定の挙動を PoC テスト計画へ追加。
  - CLI `uv run pptx outline ... --show-layout-reasons` の実行結果で `layout_score_detail` が含まれることを確認する統合テスト。
