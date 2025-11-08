# 工程3 マッピング (HITL + 自動) 設計

## 目的
- 工程2の BriefCard とテンプレ構造（`jobspec.json` / `layouts.jsonl`）を突合し、工程4（PPTX 作成）が参照する `generate_ready.json` を生成する。
- HITL 承認と割当ログを `generate_ready_meta.json`・`draft_review_log.json`・`draft_mapping_log.json` に集約し、監査しやすい構造を維持する。
- 再実行や差戻しが発生した際も `.pptx/draft/` 配下の成果物を固定し、CLI／自動化から運用できるようにする。

## コンポーネント
| コンポーネント | 役割 | 技術 | 備考 |
| --- | --- | --- | --- |
| Slide ID Aligner (新規) | BriefCard ↔ JobSpec の card/slide ID を AI で突合 | Python / content_ai | `content_approved` の `ContentSlide.id` を補正、監査ログへ出力 |
| Draft Structuring Engine | 章構成・差戻しワークフロー | Python / dataclass | `generate_ready_meta.sections[]`・`draft_review_log.json` を管理 |
| Layout Hint Engine | レイアウト候補スコアリング | Python | Brief の intent / chapter / Analyzer 指摘を参照 |
| GenerateReady Builder | プレースホルダ割付・フォールバック制御 | Python | `generate_ready.json`, `draft_mapping_log.json` を生成 |
| CLI | `pptx compose` / `pptx outline` | Click | compose が工程3全体をラップし、outline が構成再実行を担う |

## 入出力
- 入力: `jobspec.json`, `layouts.jsonl`, `prepare_card.json`, `brief_log.json`, `ai_generation_meta.json`,（任意）`analysis_summary.json`、章テンプレ辞書、差戻し理由辞書。
- 出力: `generate_ready.json`, `generate_ready_meta.json`, `draft_review_log.json`, `draft_mapping_log.json`, `fallback_report.json`。

## ワークフロー概要
1. `pptx compose` が Brief 成果物とテンプレ構造を読み込み、章テンプレ辞書 (`config/chapter_templates/`) に基づいて初期章構成を作成する。
2. Slide ID Aligner が `prepare_card.json` と `jobspec.json` を参照し、AI マッチングでカード ↔ スライド ID を突合。採用された ID は `content_approved` に反映し、信頼度や未確定カードをログへ記録する。
3. `CardLayoutRecommender` がカード単位でレイアウト候補を算出し、スコア内訳と共に `draft_mapping_log.json` に記録する。Analyzer 連携がある場合は重大度情報を候補に付与する。
4. HITL が CLI から章・スライド単位で承認／差戻し／付録送りを行い、操作履歴を `draft_review_log.json` に追記する。差戻し理由コードは `return_reasons.json` の定義に従って必須入力とする。
5. GenerateReady Builder が承認済みカードをテンプレ構造と突合し、フォールバック（縮約→分割→付録送り）を適用しながら `generate_ready.json` を生成する。
6. `generate_ready_meta.json` を出力し、章テンプレ適合率、承認統計、AI 推薦採用件数、Analyzer サマリ、監査メタ情報を集約する。

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
| `--target-length <int>` | 目標スライド枚数 | 未指定 |
| `--structure-pattern <name>` | 章構成パターン名 | 未指定 |
| `--appendix-limit <int>` | 付録枚数の上限 | `5` |
| `--chapter-templates-dir <dir>` | 章テンプレート辞書ディレクトリ | `config/chapter_templates` |
| `--chapter-template <id>` | 強制適用する章テンプレート ID | 未指定 |
| `--import-analysis <path>` | `analysis_summary.json` のパス | 未指定 |
| `--layouts <path>` | テンプレ構造 (`layouts.jsonl`) | jobspec の meta から解決 |
| `--output, -o <dir>` | `generate_ready.json` 等の出力ディレクトリ | `.pptx/compose` |
| `--rules <path>` | 検証ルール設定ファイル | `config/rules.json` |
| `--template, -t <path>` | テンプレートファイル | jobspec の meta から解決 |
| `--branding <path>` | ブランド設定ファイル | `config/branding.json` |
| `--show-layout-reasons` | レイアウト候補のスコア内訳を表示 | 無効 |

- ドラフト関連の追加オプション: `--target-length`, `--structure-pattern`, `--appendix-limit`, `--chapter-template` など。詳細は CLI リファレンスを参照。

### `pptx outline`
- ドラフト構成のみを再実行する際に利用。`--brief-*` オプションは `compose` と共通。
- 差戻し後に Draft のみ更新したいケースや UI 連携での個別更新時に利用する。

### `pptx mapping`
- 工程3のマッピング処理だけを個別に実行し、`.pptx/gen/`（既定）配下に `generate_ready.json` などを生成するコマンド。
- `pptx compose` とほぼ同じオプションを持ち、Brief 成果物・テンプレート解決の扱いも共通。レンダリング工程（工程4）は `pptx gen` が担当する。

## ログ・監査
- `draft_review_log.json`: 章/スライドの承認・差戻し履歴（`action`, `actor`, `timestamp`, `reason_code`, `notes`）。
- `draft_mapping_log.json`: レイアウト候補スコア、AI 補完、フォールバック履歴、Analyzer サマリ。
- `fallback_report.json`: 重大フォールバックの詳細（適用戦略、対象スライド、理由）。
- `generate_ready_meta.json` には章テンプレ適合率、承認統計、AI 推薦採用件数などを記録し、ハッシュ情報は別途 `audit_log.json` に集約する。

## 品質ゲート
- `jobspec.json.slides[*].id` に含まれる ID はすべて `content_approved.slides[*].id` に存在することを必須とし、不一致が 1 件でも見つかった場合は `DraftStructuringError` を送出して工程3を即時停止する。エラーメッセージには欠損 ID 一覧を含め、CLI 側では exit code 6 として扱う。
- Slide ID Aligner が `content_approved` を補正した後も未解決の ID が残るケースを前提とし、品質ゲートに到達する前に INFO ログで検出状況を通知する。
- 例外発生時は `.pptx/draft/` 配下へ中間成果物を出力せず、HITL は `prepare_card.json` / `jobspec.json` を突合して ID 設定ミスを修正した上で再実行する。

## Analyzer 連携
- `analysis_summary.json` を `--analysis-summary` で読み込み、重大度 High の指摘があるカードには `analyzer_context` を付与する。
- Analyzer 指摘件数が閾値を超える場合は候補スコアを減点し、差戻しを優先表示する。

## 未解決事項
- 章テンプレ適合率の計算ロジックと Stage4 の `generate_ready_meta.template` との整合。
- レイアウト候補スコアの ML 化と継続学習。
- `draft_mapping_log.json` のダイジェスト表示（CLI/監視ダッシュボード）実装。
- Analyzer 指摘と差戻し理由コードの自動マッピング。
