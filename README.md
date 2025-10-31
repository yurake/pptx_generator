<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/pptx_generator_logo_black.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/pptx_generator_logo_white.png">
    <img src="assets/pptx_generator_logo_white.png" alt="PPTX GENERATOR">
  </picture>
</p>


構造化されたプレゼン仕様を読み取り、ブランド統一された PowerPoint と PDF を短時間で作成する自動化ツールです。

## 主な機能
- プレゼン仕様 JSON（例: `samples/json/sample_jobspec.json`、`slides` 配列や `meta` 情報を含む構造化データ）から PPTX を生成し、必要に応じて LibreOffice 経由で PDF を併産する。
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
| 6. PPTX レンダリング | 自動 | `rendering_ready.json`、テンプレート、ブランド設定 | PPTX、PDF（任意）、`analysis.json`、`rendering_log.json`、`audit_log.json`、`review_engine_analyzer.json` | テンプレ適用と最終出力を生成し、整合チェックと監査メタを記録 |

工程 3・4 では人による承認（HITL）が必須です。AI レビューや承認フローの仕様は `docs/design/schema/README.md` と `docs/requirements/requirements.md` にまとめています。

## このドキュメントの読み方
- まずは「クイックスタート」で環境構築と基本フローを確認します。
- 詳細な CLI 手順を探す場合は「CLI チートシート」へ。各工程のガイドラインや要件は `docs/requirements/stages/`、設計の詳細は `docs/design/` を参照してください。
- FAQ や運用メモは `docs/runbooks/`、テンプレート運用ルールは `docs/policies/` にまとまっています。

## クイックスタート

### セットアップ
1. Python 3.12 系の仮想環境を用意し、有効化します。
2. 依存パッケージを同期します。
   ```bash
   uv sync
   ```
   - 権限エラーが発生する環境では `UV_CACHE_DIR=.uv-cache uv sync` を使用します。
3. CLI が動作することを確認します。
   ```bash
   uv run --help
   ```
4. LibreOffice を利用する場合は headless 実行を確認します（任意）。
   ```bash
   soffice --headless --version
   ```

### 基本ワークフロー（6 工程）
| 工程 | やること | 主な入力 | 代表 CLI |
| --- | --- | --- | --- |
| 1. テンプレ準備 | ブランド別テンプレートとスタイル資産を整える | PPTX テンプレート | `pptx tpl-release` |
| 2. テンプレ構造抽出 | レイアウトとアンカー情報を JSON 化する | テンプレート PPTX | `pptx tpl-extract` |
| 3. コンテンツ正規化 (HITL) | スライド内容を整形し承認する | `spec.json` / ドラフト資料 | `pptx content` |
| 4. ドラフト構成設計 (HITL) | 章立てとページ順を決める | 承認済みコンテンツ | `pptx outline` |
| 5. マッピング | レイアウト割付とプレースホルダ設定 | `draft_approved.json` | `pptx mapping` |
| 6. レンダリング | PPTX/PDF を生成し監査メタを出力 | `rendering_ready.json` | `pptx render` / `pptx gen` |

補足資料:
- 要件: `docs/requirements/requirements.md`
- 設計: `docs/design/design.md`
- 運用メモ: `docs/runbooks/`

## CLI チートシート

| 目的 | コマンド例 | 出力 | 補足 |
| --- | --- | --- | --- |
| テンプレ抽出 | `uv run pptx tpl-extract --template samples/templates/templates.pptx` | `.pptx/extract/` にテンプレ構造とブランド設定 | 指定ファイルのみで実行可能 |
| テンプレリリースメタ生成 | `uv run pptx tpl-release --template samples/templates/templates.pptx --brand demo --version v1` | `.pptx/release/` にリリースメタ | `--brand` / `--version` は任意の識別子を指定 |
| 工程3 承認適用 | `uv run pptx content samples/json/sample_jobspec.json --content-approved samples/json/sample_content_approved.json` | `.pptx/content/` に `spec_content_applied.json` | サンプル承認データを適用 |
| 工程4 ドラフト生成 | `uv run pptx outline .pptx/content/spec_content_applied.json` | `.pptx/draft/` にドラフト成果物 | 工程3の出力をそのまま入力 |
| 工程5 マッピング | `uv run pptx mapping .pptx/content/spec_content_applied.json --template samples/templates/templates.pptx` | `.pptx/gen/rendering_ready.json` | テンプレ指定でブランド整合を確認 |
| 全工程一括 | `uv run pptx gen samples/json/sample_jobspec.json --template samples/templates/templates.pptx` | `.pptx/gen/` に PPTX/PDF/ログ | 既定設定のまま一括実行 |

CLI の詳細なオプションは各サブコマンドに対して `uv run pptx <cmd> --help` を参照してください。

## 工程別ガイド概要
ここでは各工程の目的と主要な参照ドキュメントをまとめます。詳細な手順やチェックリストはリンク先を参照してください。

> `pptx` ルートコマンドには `-v/--verbose`（INFO レベル）と `--debug`（DEBUG レベル）のログオプションがあります。生成AIモードのプロンプト／レスポンス詳細はこれらのオプションを付与した場合に出力されます。

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
     --golden-spec samples/json/sample_jobspec.json
   ```
   - 既定の出力先は `.pptx/release/` です。`template_release.json`（受け渡しメタ）や `release_report.json`（差分レポート）、`golden_runs/`（ゴールデンサンプル検証ログ）が保存されます。
   - `--baseline-release` で過去バージョンとの差分比較が可能です。`--golden-spec` を複数指定すると代表 spec でのレンダリング検証をまとめて実行します。

### 工程 2: テンプレ構造抽出
- テンプレート PPTX からレイアウトとアンカー情報を抽出し、`layouts.jsonl` と `branding.json` を生成します。
- 差分チェックや品質検証には `pptx layout-validate` を併用します。
- 詳細ガイド: `docs/requirements/stages/stage-02-template-structure-extraction.md`

### 工程 3: コンテンツ正規化
- 入力 JSON をスライド候補へ整形し、HITL で `content_approved.json` を確定します。生成AIドラフトの作成やレビュー支援は `pptx content` コマンドで行い、生成AIモードが既定です。
- ガイドラインは `docs/requirements/stages/stage-03-content-normalization.md` を参照してください。
- `.pptx/content/` 配下に `content_draft.json`（生成AIモード時）、`content_ai_log.json`、`ai_generation_meta.json`、`spec_content_applied.json`、`content_meta.json` を出力します。
  ```bash
  # 生成AIドラフトを作成（content_draft.json などを出力）
  uv run pptx content samples/json/sample_jobspec.json \
    --content-source samples/contents/sample_import_content.txt \
    --output .pptx/content

  # 承認済み JSON を適用する場合
  uv run pptx content samples/json/sample_jobspec.json \
    --content-approved samples/json/sample_content_approved.json \
    --content-review-log samples/json/sample_content_review_log.json \
    --output .pptx/content
  ```
  - 承認済み JSON を適用したい場合は `--content-approved` / `--content-review-log` を指定します。
  - プレーンテキスト・PDF・URL など外部ソースから取り込む場合は `--content-source` を利用します。

### 工程 4: ドラフト構成設計
- 章立てやページ順を確定し、HITL で `draft_approved.json` を承認します。
- レイアウト選定の指針は `docs/requirements/stages/stage-04-draft-structuring.md` を参照してください。
- 承認済みコンテンツからドラフト成果物を生成する場合は `pptx outline`（新名称）を利用します。
  ```bash
  uv run pptx outline samples/json/sample_jobspec.json \
    --content-approved samples/json/sample_content_approved.json \
    --output .pptx/draft
  # `draft_draft.json` / `draft_approved.json` / `draft_meta.json` を確認
  ```

### 工程 5: マッピング
- `draft_approved.json` を入力にレイアウトスコアリングとフォールバック制御を行い、`rendering_ready.json`・`mapping_log.json`・必要に応じて `fallback_report.json` を生成します。`mapping_log.json` には Analyzer 指摘サマリ（件数集計・スライド別詳細）が追加されており、補完やフォールバック制御の判断材料として活用します。詳細は `docs/requirements/stages/stage-05-mapping.md` と `docs/design/stages/stage-05-mapping.md` を参照してください。
- 実行手順:
  ```bash
  uv run pptx mapping samples/json/sample_jobspec.json \
    --content-approved samples/json/sample_content_approved.json \
    --content-review-log samples/json/sample_content_review_log.json \
    --template samples/templates/templates.pptx
  # 完了後に `.pptx/gen/rendering_ready.json` や `mapping_log.json` を確認
  ```
- `pptx gen` を実行した場合も内部で `mapping` → `render` が順に呼び出され、従来どおりの成果物を `.pptx/gen/` に保存します。

### 工程 6: PPTX レンダリング
- `pptx render` サブコマンドで `rendering_ready.json` を入力し、PPTX・`analysis.json`・Review Engine 連携ファイル（`review_engine_analyzer.json`）、必要に応じて PDF を生成します。
  ```bash
  # 工程5の成果物からレンダリングのみを再実行する例
  uv run pptx mapping samples/json/sample_jobspec.json --output .pptx/gen
  uv run pptx render .pptx/gen/rendering_ready.json \
    --template samples/templates/templates.pptx \
    --output .pptx/gen
  ```
- `pptx gen` を利用すると工程3〜6を一括実行できます。
- 詳細ガイド: `docs/requirements/stages/stage-06-rendering.md`

## 主な成果物
- PPTX: `proposal.pptx`（`--pptx-name` で変更可能）
- PDF: `proposal.pdf`（`--export-pdf` 指定時）
- `analysis.json`: Analyzer/Refiner の診断結果
- `review_engine_analyzer.json`: Analyzer の issues/fixes を Review Engine 用 `grade`・Auto-fix JSON Patch に変換したファイル
- `analysis_snapshot.json`: `--emit-structure-snapshot` 指定時に出力されるアンカー構造スナップショット
- `content_draft.json` / `content_ai_log.json` / `ai_generation_meta.json`: 生成AIモードで出力されるドラフト本文・プロンプトログ・メタ情報
- `spec_content_applied.json`: `--content-approved` 指定時に生成される承認内容適用済み Spec のスナップショット
- `content_meta.json`: 承認済みコンテンツ／レビュー ログのハッシュや件数をまとめたメタ情報
- `rendering_ready.json`: マッピング工程で確定したレイアウトとプレースホルダ割付（`pptx mapping` または `pptx gen` 実行時に生成）
- `rendering_log.json`: レンダリング監査結果（検出済み要素・警告コード・空プレースホルダー件数）
- `mapping_log.json`: レイアウト候補スコア、フォールバック履歴、AI 補完ログ、Analyzer 指摘サマリ（件数・スライド別内訳）
- `fallback_report.json`: フォールバック発生スライドの一覧（発生時のみ）
- `outputs/audit_log.json`: 生成時刻や成果物ハッシュ、レンダリング警告サマリ、`pdf_export` / `polisher` メタ（リトライ回数・処理時間・サマリ JSON）。
- `draft_draft.json` / `draft_approved.json`: Draft API / CLI が利用する章構成データ（`--draft-output` ディレクトリに保存）
- `draft_review_log.json`: Draft 操作ログ（`--draft-output` ディレクトリに保存）
- `draft_meta.json`: `pptx outline` が出力する章数・スライド数・承認状況のメタ情報
- `branding.json`: テンプレ抽出時に `.pptx/extract/` へ保存
- 解析結果の詳細な読み方と運用手順は `docs/runbooks/pptx-analyzer.md` を参照。

## 詳細コマンドリファレンス

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
| `--polisher/--no-polisher` | Open XML Polisher を実行するかを指定 | ルール設定の値 |
| `--polisher-path <path>` | Polisher 実行ファイル（`.exe` / `.dll` 等）を明示する | `config/rules.json` の `polisher.executable` または環境変数 |
| `--polisher-rules <path>` | Polisher 用ルール設定ファイルを差し替える | `config/rules.json` の `polisher.rules_path` |
| `--polisher-timeout <sec>` | Polisher 実行のタイムアウト秒数 | `polisher.timeout_sec` |
| `--polisher-arg <value>` | Polisher に追加引数を渡す（複数指定可 / `{pptx}`, `{rules}` プレースホルダー対応） | 指定なし |
| `--polisher-cwd <dir>` | Polisher 実行時のカレントディレクトリを固定する | カレントディレクトリ |
| `--content-approved <path>` | 工程3の `content_approved.json` を適用する | 指定なし |
| `--content-review-log <path>` | 工程3の承認ログ JSON (`content_review_log.json`) を適用する | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` を参照し layout_hint 候補を算出する | 指定なし |
| `--draft-output <dir>` | `draft_draft.json` / `draft_approved.json` / `draft_review_log.json` の出力先 | `.pptx/draft` |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 | 無効 |
| `--verbose` | 追加ログを表示する | 無効 |

#### `pptx content`

- 生成AIを利用したドラフト生成が既定です。`config/content_ai_policies.json` をロードし、`src/pptx_generator/content_ai/prompts.py` に定義された `prompt_id` をもとにスライド案を出力します。
- `--content-source` でプレーンテキスト／PDF／URL からのインポート、`--content-approved` で承認済み JSON の適用が可能です。これらを指定した場合は非生成AIモードへ切り替わります。
- `--ai-policy` でポリシー定義ファイルを差し替え、`--ai-policy-id` で適用するポリシーを明示できます（未指定時は `default_policy_id` を利用）。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/content` |
| `--spec-output <filename>` | 承認内容を適用した Spec のファイル名 | `spec_content_applied.json` |
| `--normalized-content <filename>` | 正規化した `content_approved.json` の保存名 | `content_approved.json` |
| `--review-output <filename>` | 承認イベントログの正規化ファイル名 | `content_review_log.json` |
| `--meta-filename <filename>` | 承認メタ情報のファイル名 | `content_meta.json` |
| `--content-source <value>` | プレーンテキスト / PDF / URL からドラフトを生成 | 指定なし |
| `--ai-policy <path>` | 生成AIポリシー定義 JSON を差し替える | `config/content_ai_policies.json` |
| `--ai-policy-id <value>` | 利用するポリシー ID | `default_policy_id` |
| `--ai-output <filename>` | 生成ログ（プロンプト、警告）の出力名 | `content_ai_log.json` |
| `--ai-meta <filename>` | 生成メタ情報の出力名 | `ai_generation_meta.json` |
| `--slide-count <int>` | 生成するスライド枚数（未指定は LLM の判断、mock 時は 5 枚） | 指定なし |
| `--content-approved <path>` | 承認済みコンテンツ JSON | 指定なし |
| `--content-review-log <path>` | 承認イベントログ JSON | 指定なし |

**プロバイダー切り替え（環境変数）**
- CLI 起動時に `.env` が自動で読み込まれるため、環境変数は `.env` へ記述して管理できます。
- `PPTX_LLM_PROVIDER`: `mock`（既定） / `openai` / `azure-openai` / `claude` / `aws-claude`
- **OpenAI**: `OPENAI_API_KEY`, 任意で `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`
- **Azure OpenAI**: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, 任意で `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_TEMPERATURE`, `AZURE_OPENAI_MAX_TOKENS`
- **Claude API**: `ANTHROPIC_API_KEY`, 任意で `ANTHROPIC_MODEL`, `ANTHROPIC_TEMPERATURE`, `ANTHROPIC_MAX_TOKENS`
- **AWS Claude (Bedrock)**: `AWS_CLAUDE_MODEL_ID`, 任意で `AWS_REGION`, `AWS_CLAUDE_TEMPERATURE`, `AWS_CLAUDE_MAX_TOKENS`
- 各プロバイダーを利用する際は対応する SDK（`openai`, `anthropic`, `boto3` など）を追加インストールしてください。

#### `pptx outline`

- 承認済みコンテンツを読み込み、ドラフト案 (`draft_draft.json`) と承認済みドラフト (`draft_approved.json`) を生成します。`content_approved` を指定しない場合は Spec に含まれる内容をそのまま利用します。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/draft` |
| `--draft-filename <filename>` | ドラフト案ファイル名 | `draft_draft.json` |
| `--approved-filename <filename>` | 承認済みドラフトファイル名 | `draft_approved.json` |
| `--log-filename <filename>` | ドラフトレビュー ログのファイル名 | `draft_review_log.json` |
| `--meta-filename <filename>` | ドラフトメタ情報のファイル名 | `draft_meta.json` |
| `--content-approved <path>` | 承認済みコンテンツ JSON | 指定なし |
| `--content-review-log <path>` | 承認イベントログ JSON | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` | 指定なし |
| `--target-length <int>` | 目標スライド枚数 | Spec から推定 |
| `--structure-pattern <text>` | 章構成パターン名 | `custom` |
| `--appendix-limit <int>` | 付録枚数の上限 | 5 |

#### `pptx mapping`

- 工程5のみを実行し、`rendering_ready.json` と `mapping_log.json` を生成します。`pptx gen` でも内部的に利用されます。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/gen` |
| `--rules <path>` | 文字数や段落レベル制限を定義したルールを指定 | `config/rules.json` |
| `--content-approved <path>` | 工程3の `content_approved.json` を適用する | 指定なし |
| `--content-review-log <path>` | 工程3の承認ログ JSON (`content_review_log.json`) を適用する | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` を参照し layout_hint 候補を算出する | 指定なし |
| `--draft-output <dir>` | `draft_draft.json` / `draft_approved.json` / `draft_review_log.json` の出力先 | `.pptx/draft` |
| `--template <path>` | ブランド抽出に使用するテンプレート（メタ情報に記録） | 指定なし |
| `--branding <path>` | ブランド設定 JSON を差し替える | `config/branding.json` |

#### `pptx render`

- `rendering_ready.json` を入力に工程6を実行し、PPTX・分析結果・必要に応じて PDF を生成します。`pptx gen` は `mapping` の成果物を引き渡してこのコマンド相当の処理を行います。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/gen` |
| `--template <path>` | 利用する `.pptx` テンプレートを指定 | 同梱テンプレート |
| `--pptx-name <filename>` | 出力 PPTX 名を変更する | `proposal.pptx` |
| `--rules <path>` | Analyzer 設定を含むルールファイル | `config/rules.json` |
| `--branding <path>` | ブランド設定 JSON を差し替える | `config/branding.json` |
| `--export-pdf` | LibreOffice 経由で PDF を同時生成 | 無効 |
| `--pdf-mode <both\|only>` | PDF のみ出力するかを選択 | `both` |
| `--pdf-output <filename>` | 出力 PDF 名を変更する | `proposal.pdf` |
| `--libreoffice-path <path>` | `soffice` のパスを明示する | `PATH` から探索 |
| `--pdf-timeout <sec>` | LibreOffice 実行のタイムアウト秒数 | 120 |
| `--pdf-retries <count>` | PDF 変換のリトライ回数 | 2 |
| `--polisher/--no-polisher` | Open XML Polisher を実行するかを指定 | ルール設定の値 |
| `--polisher-path <path>` | Polisher 実行ファイル（`.exe` / `.dll` 等）を明示する | `config/rules.json` の `polisher.executable` または環境変数 |
| `--polisher-rules <path>` | Polisher 用ルール設定ファイルを差し替える | `config/rules.json` の `polisher.rules_path` |
| `--polisher-timeout <sec>` | Polisher 実行のタイムアウト秒数 | `polisher.timeout_sec` |
| `--polisher-arg <value>` | Polisher に追加引数を渡す（複数指定可 / `{pptx}`, `{rules}` プレースホルダー対応） | 指定なし |
| `--polisher-cwd <dir>` | Polisher 実行時のカレントディレクトリを固定する | カレントディレクトリ |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 | 無効 |
| `--verbose` | 追加ログを表示する | 無効 |

> `pptx gen` は内部で `pptx mapping` → `pptx render` を順番に実行します。工程ごとに再実行したい場合は新設コマンドを利用してください。

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
  - `summary` にレイアウト数・アンカー数・警告/エラー件数・Analyzer 指標を集計
  - `environment` に Python / CLI / LibreOffice / .NET SDK のバージョンメタを記録
- `release_report.json`: 過去バージョンとの差分レポート（`--baseline-release` 時）
- `golden_runs.json`／`golden_runs/<spec名>/`: ゴールデンサンプル検証結果 (`--golden-spec` 指定時)
- ゴールデンサンプルで失敗がある場合は exit code 6 で終了します
- `--baseline-release` を指定し `--golden-spec` を省略した場合、ベースラインの `golden_runs` に含まれる spec を自動で再実行します（見つからない spec は警告扱い）。

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
