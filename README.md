# pptx_generator

構造化されたプレゼン仕様を読み取り、ブランド統一された PowerPoint と PDF を短時間で作成する自動化ツールです。

## 主な機能
- プレゼン仕様 JSON（例: `samples/json/sample_spec.json`、`slides` 配列や `meta` 情報を含む構造化データ）から PPTX を生成し、必要に応じて LibreOffice 経由で PDF を併産する。
- PPTX テンプレートからレイアウト構造とブランド設定を抽出し、再利用可能な JSON 雛形を自動生成する。
- Analyzer／Refiner による簡易診断でスライド品質をチェックし、修正ポイントを抽出する。

プレゼン仕様 JSON は工程 3・4 の HITL 作業で整備する想定です。現時点ではテキスト資料から自動変換する機能は提供していませんが、テンプレ抽出結果や既存サンプルをコピーしてカスタマイズする運用が可能です。

## アーキテクチャ概要
本プロジェクトは 6 工程で資料を生成します。詳細は `docs/notes/20251011-roadmap-refresh.md` と `docs/design/design.md` を参照してください。

| 工程 | 実行主体 | 主な入力 | 主な成果物 | 概要 |
| --- | --- | --- | --- | --- |
| 1. テンプレ準備 | 自動＋HITL | 既存テンプレート資産 | テンプレートファイル、版管理ノート | ブランドごとの PPTX テンプレ資産を整備し、命名ルールを適用 |
| 2. テンプレ構造抽出 | 自動 | テンプレートファイル | レイアウト JSON、`branding.json` | テンプレからレイアウト構造 JSON と layout-style 定義を生成 |
| 3. コンテンツ正規化 | HITL | プレゼン仕様 JSON (`slides`) | `content_approved.json` | 入力データをスライド候補へ整形し、承認（HITL） |
| 4. ドラフト構成設計 | HITL | `content_approved.json` | `draft_approved.json` | 章立て・ページ順・`layout_hint` を確定し、承認（HITL） |
| 5. マッピング | 自動 | `draft_approved.json` | `rendering_ready.json` | レイアウト選定とプレースホルダ割付を行い、中間 JSON を生成 |
| 6. PPTX レンダリング | 自動 | `rendering_ready.json`、テンプレート、ブランド設定 | PPTX、PDF（任意）、`analysis.json`、`review_engine_analyzer.json` | テンプレ適用と最終出力を生成 |

工程 3・4 では人による承認（HITL）が必須です。AI レビューや承認フローの仕様は `docs/design/schema/README.md` と `docs/requirements/requirements.md` にまとめています。

## 環境要件
- Python 3.12 系
- `uv` コマンド（<https://docs.astral.sh/uv/getting-started/installation/>）
- .NET 8 SDK（Open XML SDK ベースの仕上げツール構築に利用）
- LibreOffice（`soffice --headless` が利用可能であること）

## セットアップ
1. 任意の仮想環境を作成し有効化します。
2. 依存パッケージを同期します。
   ```bash
   uv sync
   ```
   - サンドボックス環境などで権限エラーが発生する場合は `UV_CACHE_DIR=.uv-cache uv sync` を使用します。
3. CLI エントリーポイントが認識できることを確認します。
   ```bash
   uv run --help
   ```
4. PDF 変換を利用する場合は LibreOffice の動作を確認します（任意）。
   ```bash
   soffice --headless --version
   ```

## 使い方
6 工程の流れに沿って作業します。詳細な業務フローは各ステージの要件ドキュメント（`docs/requirements/stages/`）を参照してください。

### 工程 1: テンプレ準備
- テンプレ資産は `templates/` で管理し、命名規約や更新手順は `docs/policies/config-and-templates.md` を参照します。
- 自動検査ツール（命名整合性チェックなど）は設計中です。運用中は手動レビュー（HITL）を併用します。
- テンプレ受け渡しメタを生成する場合はテンプレリリース CLI を利用します。
   ```bash
   uv run pptx tpl-release \
     --template templates/libraries/<brand>/<version>/template.pptx \
     --brand <brand> \
     --version <version> \
     --baseline-release templates/releases/<brand>/<prev_version>/template_release.json \
     --golden-spec samples/json/sample_spec.json
   ```
   - 既定の出力先は `.pptx/release/` です。`template_release.json`（受け渡しメタ）や `release_report.json`（差分レポート）、`golden_runs/`（ゴールデンサンプル検証ログ）が保存されます。
   - `--baseline-release` で過去バージョンとの差分比較が可能です。`--golden-spec` を複数指定すると代表 spec でのレンダリング検証をまとめて実行します。

### 工程 2: テンプレ構造抽出
- 既存テンプレートからレイアウト／アンカー情報とブランド設定を抽出します。
   ```bash
   uv run pptx tpl-extract \
     --template templates/libraries/acme/v1/template.pptx \
     --output .pptx/extract/acme_v1
   # レイアウト名で絞り込む場合
   uv run pptx tpl-extract \
     --template templates/libraries/acme/v1/template.pptx \
     --output .pptx/extract/acme_v1 \
     --layout "タイトルスライド"
   # YAML 形式で出力する場合
   uv run pptx tpl-extract \
     --template templates/libraries/acme/v1/template.pptx \
     --output .pptx/extract/acme_v1 \
     --format yaml
   ```
- 出力は既定で `.pptx/extract/` 以下に保存され、レイアウト JSON と layout-style 対応の `branding.json` が生成されます。サンプルで試す場合は `samples/templates/templates.pptx` を指定してください。
- `branding.json` では `theme` / `components` / `layouts` にスタイル設定が格納されます。詳細は `docs/design/layout-style-governance.md` を参照してください。
- 抽出結果の健全性や差分確認には検証スイートを利用します。
   ```bash
   uv run pptx layout-validate \
     --template templates/libraries/acme/v1/template.pptx \
     --output .pptx/validation/acme_v1
   # 過去の layouts.jsonl と比較する場合
   uv run pptx layout-validate \
     --template templates/libraries/acme/v1/template.pptx \
     --output .pptx/validation/acme_v1 \
     --baseline releases/acme/v0/layouts.jsonl \
     --analyzer-snapshot .pptx/gen/analysis_snapshot.json
   ```
- 生成される `layouts.jsonl` / `diagnostics.json` / `diff_report.json` は工程 2 の成果物品質を可視化し、CI などでの回帰チェックにも利用できます。

### 工程 3: コンテンツ正規化
- 入力 JSON をスライド候補へ整形し、HITL で `content_approved.json` を作成します。
- ガイドラインは `docs/requirements/stages/stage-03-content-normalization.md` にまとめています。

### 工程 4: ドラフト構成設計
- 章立てやページ順を確定し、HITL で `draft_approved.json` を承認します。
- レイアウト選定の指針は `docs/requirements/stages/stage-04-draft-structuring.md` を参照してください。

### 工程 5: マッピング
- `draft_approved.json` から `rendering_ready.json` を生成します。マッピングロジックは `docs/requirements/stages/stage-05-mapping.md` に整理されています。
- 現在は `pptx gen` 実行時に内部で処理され、個別 CLI 公開は検討中です。

### 工程 6: PPTX レンダリング
- `pptx gen` サブコマンドで PPTX と analysis.json、Review Engine 連携ファイル（`review_engine_analyzer.json`）、必要に応じて PDF を生成します。
   ```bash
   # 最小構成（テンプレートなし）
   uv run pptx gen samples/json/sample_spec_minimal.json

   # テンプレートとブランド設定を指定する例
   uv run pptx gen \
     samples/json/sample_spec.json \
     --template samples/templates/templates.pptx \
     --branding .pptx/extract/branding.json \
     --export-pdf
   ```
- `--output` を指定しない場合、成果物は `.pptx/gen/` に保存されます。`analysis.json` は Analyzer の診断結果、`review_engine_analyzer.json` は HITL/Review Engine が参照するグレード・Auto-fix 情報、`outputs/audit_log.json` にはジョブ履歴が追記されます。`--emit-structure-snapshot` を有効化すると、テンプレ構造との突合に利用できる `analysis_snapshot.json` も併せて保存されます。

### 生成物の確認
- PPTX: `proposal.pptx`（`--pptx-name` で変更可能）
- PDF: `proposal.pdf`（`--export-pdf` 指定時）
- `analysis.json`: Analyzer/Refiner の診断結果
- `review_engine_analyzer.json`: Analyzer の issues/fixes を Review Engine 用 `grade`・Auto-fix JSON Patch に変換したファイル
- `analysis_snapshot.json`: `--emit-structure-snapshot` 指定時に出力されるアンカー構造スナップショット
- `rendering_ready.json`: マッピング工程で確定したレイアウトとプレースホルダ割付
- `mapping_log.json`: レイアウト候補スコア、フォールバック履歴、AI 補完ログ
- `fallback_report.json`: フォールバック発生スライドの一覧（発生時のみ）
- `outputs/audit_log.json`: 生成時刻や PDF 変換結果の履歴
- `draft_draft.json` / `draft_approved.json`: Draft API / CLI が利用する章構成データ（`--draft-output` ディレクトリに保存）
- `draft_review_log.json`: Draft 操作ログ（`--draft-output` ディレクトリに保存）
- `branding.json`: テンプレ抽出時に `.pptx/extract/` へ保存
- 解析結果の詳細な読み方と運用手順は `docs/runbooks/pptx-analyzer.md` を参照。

### コマンドリファレンス

#### `pptx gen`

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--template <path>` | 利用する `.pptx` テンプレートを指定 | 同梱テンプレート |
| `--branding <path>` | ブランド設定 JSON を差し替える<br>（テンプレート指定時は自動抽出が既定） | `config/branding.json` |
| `--rules <path>` | 文字数や段落レベル制限を定義したルールを指定 | `config/rules.json` |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/gen` |
| `--pptx-name <filename>` | 出力 PPTX 名を変更する | `proposal.pptx` |
| `--export-pdf` | LibreOffice 経由で PDF を同時生成 | 無効 |
| `--pdf-mode <both\|only>` | PDF のみ出力するかを選択 | `both` |
| `--pdf-output <filename>` | 出力 PDF 名を変更する | `proposal.pdf` |
| `--libreoffice-path <path>` | `soffice` のパスを明示する | `PATH` から探索 |
| `--pdf-timeout <sec>` | LibreOffice 実行のタイムアウト秒数 | 120 |
| `--pdf-retries <count>` | PDF 変換のリトライ回数 | 2 |
| `--content-approved <path>` | 工程3の `content_approved.json` を適用する | 指定なし |
| `--content-review-log <path>` | 工程3の承認ログ JSON (`content_review_log.json`) を適用する | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` を参照し layout_hint 候補を算出する | 指定なし |
| `--draft-output <dir>` | `draft_draft.json` / `draft_approved.json` / `draft_review_log.json` の出力先 | `.pptx/draft` |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 | 無効 |
| `--verbose` | 追加ログを表示する | 無効 |

#### `pptx tpl-extract`

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--template <path>` | 解析する `.pptx` テンプレート（必須） | - |
| `--output <dir>` | 抽出結果を保存するディレクトリ | `.pptx/extract` |
| `--layout <keyword>` | レイアウト名（前方一致）で抽出対象を絞る | 全レイアウト |
| `--anchor <keyword>` | アンカー名（前方一致）で抽出対象を絞る | 全アンカー |
| `--format <json\|yaml>` | 出力形式を選択 | `json` |
| `--verbose` | 詳細ログを表示 | 無効 |

#### `pptx tpl-release`

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--template <path>` | リリース対象のテンプレート（必須） | - |
| `--brand <name>` | ブランド名（必須） | - |
| `--version <value>` | テンプレートのバージョン（必須） | - |
| `--template-id <value>` | リリース ID。未指定時は `<brand>_<version>` を自動生成 | 自動生成 |
| `--output <dir>` | リリース成果物の出力先 | `.pptx/release` |
| `--generated-by <name>` | リリース実施者 | 空 |
| `--reviewed-by <name>` | レビュー担当者 | 空 |
| `--baseline-release <path>` | 過去の `template_release.json` と比較する | 比較なし |
| `--golden-spec <spec.json>` | ゴールデンサンプル検証に用いる spec（複数指定可） | 指定なし |
| `--verbose` | 詳細ログを表示 | 無効 |

生成物:
- `template_release.json`: テンプレ受け渡しメタ情報と診断結果
- `release_report.json`: 過去バージョンとの差分レポート（`--baseline-release` 時）
- `golden_runs.json`／`golden_runs/<spec名>/`: ゴールデンサンプル検証結果 (`--golden-spec` 指定時)
- ゴールデンサンプルで失敗がある場合は exit code 6 で終了します

#### `pptx layout-validate`

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--template <path>` | 検証対象の `.pptx` テンプレート（必須） | - |
| `--output <dir>` | 検証成果物を保存するディレクトリ | `.pptx/validation` |
| `--template-id <value>` | `layouts.jsonl` に記録するテンプレート ID。未指定時はファイル名から導出 | 自動導出 |
| `--baseline <path>` | 過去に出力した `layouts.jsonl` と比較し差分を算出する | 比較なし |
| `--analyzer-snapshot <path>` | `pptx gen --emit-structure-snapshot` が生成した `analysis_snapshot.json` を突合する | 未指定 |

生成物:
- `layouts.jsonl`: レイアウト ID／プレースホルダー構成／ヒント情報を JSON Lines 形式で保存
- `diagnostics.json`: 未知プレースホルダー種別や抽出エラーを `warnings` / `errors` に集計
- `diff_report.json`: `--baseline` 指定時にプレースホルダー追加・削除・座標変更を記録。Analyzer 突合のみでもアンカー差分を `issues` に含めたレポートを生成。
- exit code 6 で致命的エラー（抽出失敗・必須項目欠落など）を通知

## テスト・検証
- 全体テスト: `uv run --extra dev pytest`
- CLI 統合テストのみ: `uv run --extra dev pytest tests/test_cli_integration.py`
- テスト実行後は `.pptx/gen/` や `.pptx/extract/` の成果物を確認し、期待する PPTX／PDF／ログが生成されているかをチェックします。テスト方針の詳細は `tests/AGENTS.md` を参照してください。

## 設定とテンプレート
- `config/rules.json`: タイトル・箇条書きの文字数、段落レベル、禁止ワードを定義。
- `config/branding.json`: `version: "layout-style-v1"` のスキーマでフォント・カラー・要素別スタイル・レイアウト個別設定を定義。
- テンプレ運用ルールやブランド設定の更新手順は `config/AGENTS.md` と `docs/policies/config-and-templates.md` を参照します。

## 開発ガイドライン
- コントリビューション規約は `CONTRIBUTING.md` にまとめています。
- `docs/AGENTS.md`（ドキュメント更新ルール）や `src/AGENTS.md`（実装ガイド）を併読してください。
- 主な静的解析コマンド:
  ```bash
  uv tool run --package ruff ruff check .
  uv tool run --package black black --check .
  uv tool run --package mypy mypy src
  ```
- .NET 関連の整形は `dotnet format` を利用します。

## 参考ドキュメント
- `docs/design/design.md`: アーキテクチャ全体像
- `docs/design/schema/README.md`: 中間 JSON スキーマと AI レビュー仕様
- `docs/requirements/requirements.md`: ビジネス／機能要件
- `docs/requirements/stages/stage-0x-*.md`: 各工程の詳細要件
- `docs/notes/20251012-readme-refactor.md`: README リファクタリングの検討メモ
- `docs/roadmap/roadmap.md`: ロードマップとテーマ一覧

## ライセンス / サポート
- ライセンス: 社内利用を前提としており、公開ライセンスは未定です。
- 運用・問い合わせフローは `docs/runbooks/support.md` を参照してください。
