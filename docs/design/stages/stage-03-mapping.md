# 工程3 マッピング (HITL + 自動) 設計

## 目的
- 工程2の BriefCard とテンプレ構造（`jobspec.json` / `layouts.jsonl`）を突合し、工程4（PPTX 作成）が参照する `generate_ready.json` を生成する。
- HITL 承認と割当ログを `generate_ready_meta.json`・`draft_review_log.json`・`draft_mapping_log.json` に集約し、監査しやすい構造を維持する。
- 再実行や差戻しが発生した際も `.pptx/draft/` 配下の成果物を固定し、CLI／自動化から運用できるようにする。

## コンポーネント
| コンポーネント | 役割 | 技術 | 備考 |
| --- | --- | --- | --- |
| Draft Structuring Engine | 章構成・差戻しワークフロー | Python / dataclass | `generate_ready_meta.sections[]`・`draft_review_log.json` を管理 |
| Layout Hint Engine | レイアウト候補スコアリング | Python | Brief の intent / chapter / Analyzer 指摘を参照 |
| GenerateReady Builder | プレースホルダ割付・フォールバック制御 | Python | `generate_ready.json`, `draft_mapping_log.json` を生成 |
| CLI | `pptx compose` / `pptx outline` | Click | compose が工程3全体をラップし、outline が構成再実行を担う |

## 入出力
- 入力: `jobspec.json`, `layouts.jsonl`, `prepare_card.json`, `brief_log.json`, `ai_generation_meta.json`,（任意）`analysis_summary.json`、章テンプレ辞書、差戻し理由辞書。
- 出力: `generate_ready.json`, `generate_ready_meta.json`, `draft_review_log.json`, `draft_mapping_log.json`, `fallback_report.json`。

## ワークフロー概要
1. `pptx compose` が Brief 成果物とテンプレ構造を読み込み、章テンプレ辞書 (`config/chapter_templates/`) に基づいて初期章構成を作成する。
2. `CardLayoutRecommender` がカード単位でレイアウト候補を算出し、スコア内訳と共に `draft_mapping_log.json` に記録する。Analyzer 連携がある場合は重大度情報を候補に付与する。
3. HITL が CLI から章・スライド単位で承認／差戻し／付録送りを行い、操作履歴を `draft_review_log.json` に追記する。差戻し理由コードは `return_reasons.json` の定義に従って必須入力とする。
4. GenerateReady Builder が承認済みカードをテンプレ構造と突合し、フォールバック（縮約→分割→付録送り）を適用しながら `generate_ready.json` を生成する。
5. `generate_ready_meta.json` を出力し、章テンプレ適合率、承認統計、AI 推薦採用件数、Analyzer サマリ、監査メタ情報を集約する。

## CLI
### `pptx compose`
- 主なオプション
  | オプション | 説明 | 既定値 |
  | --- | --- | --- |
  | `<jobspec.json>` | Stage1 で抽出したジョブスペック | 必須 |
  | `--brief-cards <path>` | 工程2の BriefCard | `.pptx/prepare/prepare_card.json` |
  | `--brief-log <path>` | 工程2のレビュー ログ | `.pptx/prepare/brief_log.json` |
  | `--brief-meta <path>` | 工程2の生成メタ | `.pptx/prepare/ai_generation_meta.json` |
| `--draft-output <dir>` | ドラフト成果物のディレクトリ | `.pptx/draft` |
| `--layouts <path>` | テンプレ構造 (`layouts.jsonl`) | 任意 |
| `--analysis-summary <path>` | Analyzer サマリ | 任意 |
| `--generate-ready-filename <name>` | `generate_ready.json` のファイル名 | `generate_ready.json` |
| `--generate-ready-meta <name>` | `generate_ready_meta.json` のファイル名 | `generate_ready_meta.json` |
| `--review-log-filename <name>` | `draft_review_log.json` のファイル名 | `draft_review_log.json` |
| `--mapping-log-filename <name>` | `draft_mapping_log.json` のファイル名 | `draft_mapping_log.json` |
| `--show-layout-reasons` | レイアウト候補のスコア内訳を表示 | 無効 |
| `--return-reasons` | 差戻し理由テンプレ一覧を表示 | 無効 |

- ドラフト関連の追加オプション: `--target-length`, `--structure-pattern`, `--appendix-limit`, `--chapter-template` など。詳細は CLI リファレンスを参照。

### `pptx outline`
- ドラフト構成のみを再実行する際に利用。`--brief-*` オプションは `compose` と共通。
- 差戻し後に Draft のみ更新したいケースや UI 連携での個別更新時に利用する。

### `pptx mapping`
- 工程4（PPTX 作成）で `generate_ready.json` を入力にレンダリングを実行するコマンド。
- `--generate-ready`（必須）とテンプレートパスを受け取り、旧 `draft_*` ファイルを参照しない。

## ログ・監査
- `draft_review_log.json`: 章/スライドの承認・差戻し履歴（`action`, `actor`, `timestamp`, `reason_code`, `notes`）。
- `draft_mapping_log.json`: レイアウト候補スコア、AI 補完、フォールバック履歴、Analyzer サマリ。
- `fallback_report.json`: 重大フォールバックの詳細（適用戦略、対象スライド、理由）。
- `generate_ready_meta.json.audit` には主要ファイルのハッシュと実行統計を記録する。

## Analyzer 連携
- `analysis_summary.json` を `--analysis-summary` で読み込み、重大度 High の指摘があるカードには `analyzer_context` を付与する。
- Analyzer 指摘件数が閾値を超える場合は候補スコアを減点し、差戻しを優先表示する。

## 未解決事項
- 章テンプレ適合率の計算ロジックと Stage4 の `generate_ready_meta.template` との整合。
- レイアウト候補スコアの ML 化と継続学習。
- `draft_mapping_log.json` のダイジェスト表示（CLI/監視ダッシュボード）実装。
- Analyzer 指摘と差戻し理由コードの自動マッピング。
