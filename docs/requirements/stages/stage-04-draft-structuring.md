# 工程4 ドラフト構成設計 要件

## 概要
- 工程3で承認された `brief_cards.json` と、工程2で整備した `jobspec.json` を統合し、工程5が入力として利用する `generate_ready.json` を生成する。
- 生成AIがカード単位でテンプレート割当を提案し、HITL オペレータが承認／差戻し／付録送りなどを指示できる操作フローを提供する。
- 既存の `draft_draft.json` / `draft_approved.json` / `rendering_ready.json` を用いたワークフローは廃止し、`generate_ready` 出力へ全面移行する。

## 入力
- 工程3の `prepare_card.json`（`story.phase` / `intent_tags` / `supporting_points` などカード情報を含む）。
- 工程2の `layouts.jsonl`（利用可能なレイアウトカテゴリのヒント）。
- 制約情報（本編枚数上限、章構成テンプレ、付録方針）。
- 章テンプレ定義 (`config/chapter_templates/*.json`) と構成テンプレ適用ポリシー。
- Analyzer 連携データ（`analysis_summary.json` など工程6の集計結果）。
- 差戻し理由テンプレート辞書 (`return_reasons.json`)。

## 出力
- `generate_ready.json`: 工程5が唯一参照する構成ファイル。`slides[*]` にはテンプレートレイアウトIDとプレースホルダへ配置する要素を格納。`meta` に章情報、生成時間、`job_meta` / `job_auth` を含む。
- `generate_ready_meta.json`: 章別状態、テンプレ適合率、AI 推薦の採用状況、Analyzer 指摘要約、差戻し統計を記録。
- `draft_mapping_log.json`: カード割当処理の詳細ログ。AI 推薦スコア、ヒューリスティック理由、フォールバック履歴を保持。
- `draft_review_log.json`: HITL 操作ログ。ターゲット種別（章／スライド）、アクション（`approve`/`return`/`appendix`/`hint` 等）、操作者、差戻し理由コードを記録。
- `audit_log.json`（工程4セクション）: Approval-First Policy に基づく監査情報。CLI 実行時に更新する。

## ワークフロー
1. **文脈読み込み**: `BriefNormalizationStep` が `brief_cards`・`brief_log`・`ai_generation_meta` を検証し、`PipelineContext` に `brief_document` と互換用 `content_approved` を格納する。
2. **テンプレ解析**: `jobspec.json` を読み込み、スライドごとに利用可能アンカー、用途タグ（`layouts.jsonl` 連携）、収容目安を整理する。
3. **カード特徴抽出**: 各カードについて情報量指標（本文文字数、支援ポイント数、証憑有無）、意図タグ、ストーリー段階を算出し、テンプレへの適合度推定に利用する。
4. **AI 推薦**: カード単位で LLM へプロンプトを生成し、最適なテンプレ候補を最大 N 件返却する。プロンプトには以下を含む。
   - カード要約（メッセージ、支援ポイント、想定アウトプット種別）。
   - 利用可能なテンプレ一覧（用途タグ、収容目安、主要アンカー名）。
   - 制約条件（章テンプレ要件、本編枚数上限、付録上限）。
   - 出力形式（`layout_id`, `score`, `rationale[]`）。
   AI が失敗した場合は用途タグ一致度＋容量適合度＋多様性スコアでヒューリスティックを組み合わせる。
5. **割当計算**: 推薦結果をもとにカードとテンプレを一意にマッピングする。ルールは以下の通り。
   - `jobspec.slides` の未使用レイアウトに優先割当。該当レイアウトが不足する場合は類似タグを持つスライドにフォールバック。
   - 章テンプレ辞書に `required_sections` が定義されている場合は必須章を先に充足する。
   - 本編枚数超過時はスコア下位のカードを付録候補としてフラグ付けし、HITL が再配置できるよう明示する。
6. **HITL 操作**: CLI/UI を通じて章・スライド単位で承認／差戻し／付録送りを行う。差戻し時は `return_reasons.json` からコードを選択しメモを付与。操作結果は `draft_review_log.json` と `generate_ready_meta.json` に反映。
7. **成果物生成**: 最終的な割当結果を `generate_ready.json` と `generate_ready_meta.json` に書き出す。同時に `draft_mapping_log.json` を生成し、AI 推薦スコアやフォールバック履歴を保持する。

## 品質ゲート
- すべてのカードが `generate_ready.slides` に割り当てられているか、もしくは付録フラグが付与されている。
- `generate_ready.slides[*].meta.sources` にカード ID が必ず含まれている（トレーサビリティ担保）。
- 章テンプレ適合率がしきい値（既定 0.8）を下回る場合は警告を出し、HITL 確認を必須化する。
- 付録スライド数が `appendix_limit` を超えない。超過時は CLI が再割当を促す。
- `generate_ready_meta.statistics.cards_total == brief_cards.cards.length` を満たす。
- 差戻しログの `return_reason_code` は辞書に定義された値である。

## ログ・監査要件
- `draft_mapping_log.json` は以下の情報を保持する。
  - `card_id`: 割当対象カード。
  - `selected_layout`: 最終採用レイアウト ID。
  - `candidates[]`: AI 推薦およびヒューリスティックの候補。スコア、理由、推奨タイプ（`ai` / `heuristic`）を含む。
  - `fallback`: 容量超過などで適用したフォールバック履歴。
  - `analyzer_summary`: `analysis_summary.json` から引き継いだ重大度件数。
- `draft_review_log.json` は Approval-First Policy に従い、操作主体・タイムスタンプ・差戻し理由を必須化する。
- CLI 実行時に生成される `audit_log.json` の工程4セクションへ `generate_ready` 出力パスとハッシュ値、カード割当統計を追記する。

## CLI / API 要件
- `uv run pptx outline` の引数を以下とする。
  - 第1引数: `jobspec.json`（工程2の成果物）。
  - `--brief-cards`: 必須。`brief_cards.json` のパス。
  - `--brief-log`, `--brief-meta`: 任意。存在しない場合はスキップ。
  - `--layouts`, `--analysis-summary`, `--chapter-template`, `--appendix-limit`, `--target-length`: 任意。
  - `--output`: 出力ディレクトリ（既定 `.pptx/draft`）。
  - `--generate-ready-filename`, `--meta-filename`, `--mapping-log-filename`, `--review-log-filename`: 既定値はそれぞれ `generate_ready.json`, `generate_ready_meta.json`, `draft_mapping_log.json`, `draft_review_log.json`。
  - `--ai-recommender`: AI 推薦を有効化する設定（`auto|off|force`）。
- 廃止するオプション: `--draft-filename`, `--approved-filename` など `draft_*` 系。
- CLI 完了時に生成ファイルへの絶対パスを出力し、`generate_ready.json` の枚数と章ステータス概要を表示する。
- API 側では `POST /draft/outline` のレスポンスを `generate_ready` ベースに変更し、旧 `draft_*` フィールドは返却しない。

## データモデル（概要）
### GenerateReadyDocument
| フィールド | 型 | 説明 |
| --- | --- | --- |
| `slides[]` | `GenerateReadySlide` | テンプレレイアウト単位の描画指示。 |
| `slides[].layout_id` | string | `jobspec.slides[].layout` と一致するテンプレ ID。 |
| `slides[].elements` | dict | `jobspec` のアンカーに対応する要素。タイトル、本文、リスト、表、画像、チャート、テキストボックスを含む。 |
| `slides[].meta.section` | string | 章識別子。章テンプレ評価に利用。 |
| `slides[].meta.sources` | list[string] | 元となる `card_id` / その他参照元。 |
| `meta.template_version` | string | 使用テンプレのバージョン識別子。 |
| `meta.generated_at` | ISO8601 | 生成日時。 |
| `meta.job_meta` / `meta.job_auth` | object | `jobspec.meta` / `auth` を再掲。 |

### draft_review_log.json
| フィールド | 型 | 説明 |
| --- | --- | --- |
| `target_type` | `section` \| `slide` | 操作対象。 |
| `target_id` | string | 章 ID またはカード ID。 |
| `action` | `approve` \| `return` \| `appendix` \| `hint` \| `move` | 操作種別。 |
| `actor` | string | 操作者。 |
| `timestamp` | ISO8601 | 操作時刻。 |
| `changes` | dict | 差戻し理由コード、コメント、再割当候補など。 |

### generate_ready_meta.json
- `sections[]`: 章単位の状態とスライドリスト。`status`（`draft`/`approved`/`returned`）、`slides[].ai_recommended`、`slides[].appendix` を含む。
- `template.match_score`: 章テンプレ適合率。
- `statistics`: `cards_total`, `approved_slides`, `appendix_slides`, `ai_recommendation_used`, `analyzer_issue_counts` など。

## テスト要件
- サンプルデータ（`samples/json/sample_jobspec.json`, `samples/brief/sample_brief_cards.json`）を用いて CLI 統合テストを構築し、`generate_ready.json` に 1:1 でカードが割り当てられていることを検証する。
- AI 推薦をモック化したユニットテストを用意し、候補スコアの並びやフォールバック処理を確認する。
- テンプレ適合率がしきい値を下回るケース、付録上限超過ケース、差戻しログ付きケースのシナリオテストを実施する。

## 未実装・フォローアップ
- 差戻し理由辞書と AI 推薦ロジックの相互連携（返却理由から再推薦パターンを選択する仕組み）。
- 章テンプレ辞書の不足項目（セクション別レイアウト上限など）の定義拡張。
- `generate_ready_meta` と工程5監査ログ（`rendering_log.json` / `audit_log.json`）の突合レポート自動化。

以上を満たす設計を実装前にレビューし、承認を得たうえで開発を進める。
