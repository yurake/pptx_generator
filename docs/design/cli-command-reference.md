# CLI コマンド設計ガイド

## 目的
- CLI の各コマンドが 5 工程パイプラインのどこに位置づくかを整理し、責務や成果物、主要オプションを設計観点でまとめる。
- README のクイックスタートで触れ切れない詳細設定（Polisher・PDF 連携・AI プロバイダー切り替え等）を参照できるようにする。

## パイプライン全体像
- パイプラインは「テンプレ準備 → 構造抽出 → コンテンツ正規化 → マッピング（HITL + 自動）→ レンダリング」の 5 工程で構成される。
- `pptx gen` は工程5（レンダリング）専用コマンド。工程4で生成した `generate_ready.json` を入力として最終成果物を出力し、必要に応じて `pptx compose` / `pptx mapping` でドラフトやマッピング成果物を確認する。

### 工程1: テンプレ準備
テンプレートをブランド資産として登録し、リリースメタを生成する。

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
- `template_release.json`: テンプレ受け渡しメタと診断結果（環境メタには Python / CLI / LibreOffice / .NET SDK を記録）
- `release_report.json`: `--baseline-release` 指定時の差分レポート
- `golden_runs.json` と `golden_runs/<spec名>/`: ゴールデンサンプル検証結果（失敗時は exit code 6）
- `--baseline-release` 指定かつ `--golden-spec` 省略時はベースラインの `golden_runs` を自動再実行

### 工程2: テンプレ構造抽出
レイアウトとアンカー情報を抽出し、テンプレ構造を管理する。

#### `pptx tpl-extract`
| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--template <path>` | 解析する `.pptx` テンプレート（必須） | - |
| `--output <dir>` | 抽出結果を保存するディレクトリ | `.pptx/extract` |
| `--layout <keyword>` | レイアウト名（前方一致）で抽出対象を絞る | 全レイアウト |
| `--anchor <keyword>` | アンカー名（前方一致）で抽出対象を絞る | 全アンカー |
| `--format <json\|yaml>` | 出力形式を選択 | `json` |
| `--verbose` | 詳細ログを表示 | 無効 |

実行すると以下の成果物が同一ディレクトリに出力される。

- `template_spec.json` / `template_spec.yaml`（テンプレート仕様）
- `branding.json`（抽出したブランド設定）
- `jobspec.json`（ジョブスペック雛形）
- `layouts.jsonl` / `diagnostics.json`（レイアウト検証結果、`diff_report.json` は比較時のみ）

`tpl-extract` 完了時にレイアウト検証を自動実行するため、抽出直後の品質チェックがワンコマンドで完了する。個別検証のみを実施したい場合や出力ディレクトリを分けたい場合は、従来どおり `pptx layout-validate` を直接呼び出す。

#### `pptx layout-validate`
| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--template <path>` | 検証対象の `.pptx` テンプレート（必須） | - |
| `--output <dir>` | 検証成果物を保存するディレクトリ | `.pptx/validation` |
| `--template-id <value>` | `layouts.jsonl` に記録するテンプレート ID。未指定時はファイル名から導出 | 自動導出 |
| `--baseline <path>` | 過去に出力した `layouts.jsonl` と比較し差分を算出する | 比較なし |
| `--analyzer-snapshot <path>` | `pptx gen --emit-structure-snapshot` が生成した `analysis_snapshot.json` を突合する | 未指定 |

生成物:
- `layouts.jsonl`: プレースホルダー構成とヒント情報
- `diagnostics.json`: 未知プレースホルダーや抽出エラーの警告/エラー集計
- `diff_report.json`: `--baseline` 指定時の差分レポート（Analyzer 突合を含む）
- 致命的エラー時は exit code 6

`tpl-extract` が抽出直後に自動実行する処理と同等だが、成果物の出力ディレクトリや比較オプションを細かく調整したい場合はこちらを直接利用する。

### 工程3: コンテンツ正規化 (HITL)
承認済みコンテンツを整形し、後続工程へ渡すためのメタを生成する。抽出済みの `jobspec.json` を第一引数に指定する。

#### `pptx content`
- 既定では生成 AI モードでドラフトを生成し、`config/content_ai_policies.json` と `src/pptx_generator/content_ai/prompts.py` の `prompt_id` を利用する。
- `--content-source` や `--content-approved` を指定すると非生成モードへ切り替わり、既存資料を正規化する。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/content` |
| `--spec-output <filename>` | 承認内容適用後の Spec ファイル名 | `spec_content_applied.json` |
| `--normalized-content <filename>` | 正規化した `content_approved.json` の保存名 | `content_approved.json` |
| `--review-output <filename>` | 承認イベントログの保存名 | `content_review_log.json` |
| `--meta-filename <filename>` | 承認メタ情報ファイル名 | `content_meta.json` |
| `--content-source <value>` | プレーンテキスト / PDF / URL からドラフトを生成 | 指定なし |
| `--ai-policy <path>` | 生成 AI ポリシー定義を差し替える | `config/content_ai_policies.json` |
| `--ai-policy-id <value>` | 適用するポリシー ID | `default_policy_id` |
| `--ai-output <filename>` | 生成ログ（プロンプト、警告）の出力名 | `content_ai_log.json` |
| `--ai-meta <filename>` | 生成メタ情報の出力名 | `ai_generation_meta.json` |
| `--slide-count <int>` | 生成スライド枚数（未指定は LLM の判断、mock 時は 5 枚） | 指定なし |
| `--content-approved <path>` | 承認済みコンテンツ JSON | 指定なし |
| `--content-review-log <path>` | 承認イベントログ JSON | 指定なし |

実行例:
```bash
uv run pptx content .pptx/extract/jobspec.json \
  --content-source samples/contents/sample_import_content.txt \
  --output .pptx/content
```

**AI プロバイダー切り替え（環境変数）**
- `.env` を読み込んで `PPTX_LLM_PROVIDER` を指定する（`mock`/`openai`/`azure-openai`/`claude`/`aws-claude`）。
- OpenAI: `OPENAI_API_KEY` 必須。必要に応じて `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`。
- Azure OpenAI: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` 等を設定。
- Claude API: `ANTHROPIC_API_KEY` と任意パラメータ（`ANTHROPIC_MODEL` など）。
- AWS Claude (Bedrock): `AWS_CLAUDE_MODEL_ID` と `AWS_REGION` 等。
- 各プロバイダーに応じて `openai`, `anthropic`, `boto3` などの追加パッケージを導入する。

### 工程4: マッピング (HITL + 自動)
章構成の承認とレイアウト割付をまとめて実行し、`draft_approved.json` と `generate_ready.json` を整備する。

#### 推奨: `pptx compose`
- 工程4全体を一括で実行し、HITL 差戻し後の再実行を簡素化する。
- `--draft-output` と `--output` でドラフト成果物とマッピング成果物の出力先を分離できる。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--draft-output <dir>` | 工程4 (HITL) 成果物 (`draft_*`) の保存先 | `.pptx/draft` |
| `--output <dir>` | 工程4 (自動) 成果物 (`generate_ready.json` など) の保存先 | `.pptx/gen` |
| `--content-approved <path>` | 工程3の `content_approved.json` を適用する | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` を共有する | 指定なし |
| `--draft-filename` / `--approved-filename` / `--draft-log-filename` | ドラフト成果物のファイル名を上書きする | 既定値を継承 |
| `--draft-meta-filename` | `draft_meta.json` のファイル名 | `draft_meta.json` |
| `--rules <path>` | レイアウト割付で参照するルール設定 | `config/rules.json` |
| `--template <path>` | ブランド抽出に利用するテンプレート | 指定なし |
| `--branding <path>` | ブランド設定を明示的に指定する | `config/branding.json` |
| `--show-layout-reasons` | layout_hint スコア詳細を標準出力に表示する | 無効 |

実行例:
```bash
uv run pptx compose .pptx/extract/jobspec.json \
  --content-approved .pptx/content/content_approved.json \
  --draft-output .pptx/draft \
  --output .pptx/gen \
  --layouts .pptx/validation/layouts.jsonl
```

#### 補助: `pptx outline`
- HITL 作業を個別に実行したい場合に利用。`draft_draft.json` / `draft_approved.json` / `draft_review_log.json` / `draft_meta.json` を生成する。
- `compose` と同一のドラフト関連オプション（`--target-length`, `--structure-pattern`, `--appendix-limit`, `--chapter-template` など）が利用可能。

#### 補助: `pptx mapping`
- 自動マッピングのみ再実行したい場合に利用し、`generate_ready.json`・`mapping_log.json`・必要に応じて `fallback_report.json` を更新する。
- `compose` と共通の `--rules`, `--template`, `--branding` などのオプションを保持する。

### 工程5: レンダリング
最終成果物（PPTX/PDF）と監査ログを生成する。CLI からは工程4で生成した `generate_ready.json` を指定して `pptx gen` を実行し、レンダリング工程を完了させる。

#### `pptx gen`
- 工程4で生成した `generate_ready.json` を入力に、工程5（レンダリング）を実行するコマンド。テンプレート参照は `generate_ready.meta.template_path` を利用するため、工程4までにテンプレートの情報を埋め込んでおく必要がある。
- 工程4の成果物を事前に確認したい場合は `pptx compose` や `pptx mapping` を個別に実行し、最終成果物が必要になったタイミングで `pptx gen` を呼び出す。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--branding <path>` | ブランド設定 JSON を差し替える（未指定時はテンプレートから抽出） | `config/branding.json` |
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
| `--polisher-path <path>` | Polisher 実行ファイルを明示する | `config/rules.json` の `polisher.executable` または環境変数 |
| `--polisher-rules <path>` | Polisher 用ルール設定ファイルを差し替える | `config/rules.json` の `polisher.rules_path` |
| `--polisher-timeout <sec>` | Polisher 実行のタイムアウト秒数 | `polisher.timeout_sec` |
| `--polisher-arg <value>` | Polisher に追加引数を渡す | 指定なし |
| `--polisher-cwd <dir>` | Polisher 実行時のカレントディレクトリを固定する | カレントディレクトリ |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 | 無効 |
| `--verbose` | 追加ログを表示する | 無効 |

## 生成物とログの設計メモ
- `analysis_snapshot.json`: `--emit-structure-snapshot` 利用時に生成されるアンカー構造スナップショット。
- `content_draft.json` / `content_ai_log.json` / `ai_generation_meta.json`: 生成 AI モードで出力されるドラフト本文・プロンプトログ・メタ情報。
- `spec_content_applied.json`: `--content-approved` 指定時に生成される承認内容適用済み Spec。
- `content_meta.json`: 承認済みコンテンツとレビュー ログのハッシュや件数をまとめたメタ情報。
- `generate_ready.json`: マッピング工程で確定したレイアウトとプレースホルダー割付。
- `rendering_log.json`: レンダリング監査結果（検出要素・警告コード・空プレースホルダー件数）。
- `mapping_log.json`: レイアウト候補スコア、フォールバック履歴、Analyzer 指摘サマリ。
- `fallback_report.json`: フォールバック発生スライドの一覧（発生時のみ）。
- `outputs/audit_log.json`: 生成時刻や成果物ハッシュ、PDF/Polisher のメタ情報。
- `draft_draft.json` / `draft_approved.json`: Draft API/CLI が利用する章構成データ。
- `draft_review_log.json`: Draft 操作ログ。
- `draft_meta.json`: `pptx outline` が出力する章数・スライド数・承認状況メタ。
- `branding.json`: テンプレ抽出時に `.pptx/extract/` へ保存されるブランド設定。

## 運用上のポイント
- Polisher を有効化する場合は .NET 8 SDK を導入し、`config/rules.json` の `polisher` 設定と整合させる。
- PDF 変換機能を利用する場合は LibreOffice (headless 実行可能) を導入し、`soffice --headless --version` で動作確認する。
- CLI オプションの変更に伴う運用手順は `docs/runbooks/` を更新し、ToDo へメモを残す。
