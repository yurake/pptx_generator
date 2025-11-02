# CLI コマンド設計ガイド

## 目的
- CLI の各コマンドが 6 工程パイプラインのどこに位置づくかを整理し、責務や成果物、主要オプションを設計観点でまとめる。
- README のクイックスタートで触れ切れない詳細設定（Polisher・PDF 連携・AI プロバイダー切り替え等）を参照できるようにする。

## パイプライン全体像
- パイプラインは「テンプレ準備 → 構造抽出 → コンテンツ正規化 → 構成設計 → マッピング → レンダリング」の 6 工程で構成される。
- `pptx gen` は工程 5-6 を一括実行するファサード。必要に応じて `pptx mapping` と `pptx render` を個別に呼び出し、再実行や検証を行う。

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

### 工程3: コンテンツ正規化 (HITL)
承認済みコンテンツを整形し、後続工程へ渡すためのメタを生成する。

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

**AI プロバイダー切り替え（環境変数）**
- `.env` を読み込んで `PPTX_LLM_PROVIDER` を指定する（`mock`/`openai`/`azure-openai`/`claude`/`aws-claude`）。
- OpenAI: `OPENAI_API_KEY` 必須。必要に応じて `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`。
- Azure OpenAI: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` 等を設定。
- Claude API: `ANTHROPIC_API_KEY` と任意パラメータ（`ANTHROPIC_MODEL` など）。
- AWS Claude (Bedrock): `AWS_CLAUDE_MODEL_ID` と `AWS_REGION` 等。
- 各プロバイダーに応じて `openai`, `anthropic`, `boto3` などの追加パッケージを導入する。

### 工程4: ドラフト構成設計 (HITL)
章立てやスライド順を設計し、承認済みドラフトを出力する。

#### `pptx outline`
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

#### `pptx compose`
- 工程4のアウトライン生成と工程5のマッピングを連続実行し、`draft_*` と `rendering_ready.json` を一括で更新する。
- `pptx outline` / `pptx mapping` の主要オプションを引き継ぎ、`--draft-output` と `--output` で各工程の出力先を分離できる。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--draft-output <dir>` | 工程4成果物 (`draft_*`) の保存先 | `.pptx/draft` |
| `--output <dir>` | 工程5成果物 (`rendering_ready.json` 等) の保存先 | `.pptx/gen` |
| `--content-approved <path>` | 工程3の `content_approved.json` を適用する | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` をアウトラインとマッピングへ共有する | 指定なし |
| `--draft-filename` / `--approved-filename` / `--draft-log-filename` | 工程4のファイル名を上書きする | 既定値を継承 |
| `--draft-meta-filename` | 工程4メタ (`draft_meta.json`) のファイル名 | `draft_meta.json` |
| `--rules <path>` | マッピングで参照するルール設定 | `config/rules.json` |
| `--template <path>` | ブランド抽出に利用するテンプレート。未指定時はブランド設定 JSON を利用 | 指定なし |
| `--show-layout-reasons` | 工程4の layout_hint スコア詳細を標準出力に表示 | 無効 |

### 工程5: マッピング
レイアウト割付とプレースホルダー設定を確定し、レンダリング準備を整える。

#### `pptx mapping`
- 工程5のみを単独実行し、`rendering_ready.json` と `mapping_log.json` を生成する。`

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/gen` |
| `--rules <path>` | 文字数や段落レベル制限を定義したルールを指定 | `config/rules.json` |
| `--content-approved <path>` | 工程3の `content_approved.json` を適用する | 指定なし |
| `--content-review-log <path>` | 工程3の承認ログ JSON | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` を参照し layout_hint 候補を算出する | 指定なし |
| `--draft-output <dir>` | `draft_draft.json` / `draft_approved.json` / `draft_review_log.json` の出力先 | `.pptx/draft` |
| `--template <path>` | ブランド抽出に使用するテンプレート（メタ情報に記録） | 指定なし |
| `--branding <path>` | ブランド設定 JSON を差し替える | `config/branding.json` |

### 工程6: レンダリング
最終成果物（PPTX/PDF）と監査ログを生成する。

#### `pptx render`
- `rendering_ready.json` を入力に工程6を実行する。`pptx gen` で内部的に呼び出される処理に相当する。

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

#### `pptx gen`
- 工程5のマッピングと工程6のレンダリングを一括実行するファサード。工程ごとの成果物を確認したい場合は `pptx mapping` と `pptx render` を個別に利用する。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--template <path>` | 利用する `.pptx` テンプレートを指定 | 同梱テンプレート |
| `--branding <path>` | ブランド設定 JSON を差し替える（テンプレート指定時は自動抽出が既定） | `config/branding.json` |
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
| `--content-approved <path>` | 工程3の `content_approved.json` を適用する | 指定なし |
| `--content-review-log <path>` | 工程3の承認ログ JSON (`content_review_log.json`) を適用する | 指定なし |
| `--layouts <path>` | 工程2の `layouts.jsonl` を参照し layout_hint 候補を算出する | 指定なし |
| `--draft-output <dir>` | ドラフト成果物の出力先 | `.pptx/draft` |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 | 無効 |
| `--verbose` | 追加ログを表示する | 無効 |

## 生成物とログの設計メモ
- `analysis_snapshot.json`: `--emit-structure-snapshot` 利用時に生成されるアンカー構造スナップショット。
- `content_draft.json` / `content_ai_log.json` / `ai_generation_meta.json`: 生成 AI モードで出力されるドラフト本文・プロンプトログ・メタ情報。
- `spec_content_applied.json`: `--content-approved` 指定時に生成される承認内容適用済み Spec。
- `content_meta.json`: 承認済みコンテンツとレビュー ログのハッシュや件数をまとめたメタ情報。
- `rendering_ready.json`: マッピング工程で確定したレイアウトとプレースホルダー割付。
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
