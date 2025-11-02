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

### 工程3: ブリーフ正規化 (HITL)
ブリーフ入力（Markdown / JSON 等）を BriefCard モデルへ正規化し、後続工程が参照する成果物を生成する。

#### `pptx content`
- 既定ポリシー（`config/brief_policies/default.json`）に従って章カードを構築し、`.brief/` 配下に成果物を出力する。
- 入力形式は `BriefSourceDocument` が自動判定する。`.json` / `.jsonc` は JSON として、その他は Markdown テキストとして解析する。

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--brief-policy <path>` | ブリーフ生成ポリシー定義 | `config/brief_policies/default.json` |
| `--output <dir>` | 生成物を保存するディレクトリ | `.brief` |
| `--card-limit <int>` | 生成するカード枚数の上限 | 指定なし |
| `--ai-policy <path>` | 生成エンジンの追加設定（将来拡張用） | 指定なし |
| `--ai-policy-id <value>` | ポリシーセット内で利用する ID（将来拡張用） | 指定なし |

生成物:
- `brief_cards.json`: BriefCard の配列（章/メッセージ/補完情報を保持）
- `brief_log.json`: HITL ログ（初期状態は空配列）
- `brief_ai_log.json`: 生成時のダイアログ／ワーニングのスタブ情報
- `ai_generation_meta.json`: 生成メタ（統計・入力ハッシュ等）
- `brief_story_outline.json`: 章構成とカード紐付け
- `audit_log.json`: 生成時刻・ポリシー ID・成果物パスをまとめた監査ログ

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
| `--brief-cards <path>` | 工程3の `brief_cards.json` | `.brief/brief_cards.json` |
| `--brief-log <path>` | 工程3の `brief_log.json`（任意） | `.brief/brief_log.json` |
| `--brief-meta <path>` | 工程3の `ai_generation_meta.json`（任意） | `.brief/ai_generation_meta.json` |
| `--layouts <path>` | 工程2の `layouts.jsonl` | 指定なし |
| `--target-length <int>` | 目標スライド枚数 | Spec から推定 |
| `--structure-pattern <text>` | 章構成パターン名 | `custom` |
| `--appendix-limit <int>` | 付録枚数の上限 | 5 |

### 工程5: マッピング
レイアウト割付とプレースホルダー設定を確定し、レンダリング準備を整える。

#### `pptx mapping`
- 工程5のみを単独実行し、`rendering_ready.json` と `mapping_log.json` を生成する。`

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--output <dir>` | 生成物を保存するディレクトリ | `.pptx/gen` |
| `--rules <path>` | 文字数や段落レベル制限を定義したルールを指定 | `config/rules.json` |
| `--brief-cards <path>` | 工程3の `brief_cards.json` | `.brief/brief_cards.json` |
| `--brief-log <path>` | 工程3の `brief_log.json`（任意） | `.brief/brief_log.json` |
| `--brief-meta <path>` | 工程3の `ai_generation_meta.json`（任意） | `.brief/ai_generation_meta.json` |
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
| `--brief-cards <path>` | 工程3の `brief_cards.json` | `.brief/brief_cards.json` |
| `--brief-log <path>` | 工程3の `brief_log.json`（任意） | `.brief/brief_log.json` |
| `--brief-meta <path>` | 工程3の `ai_generation_meta.json`（任意） | `.brief/ai_generation_meta.json` |
| `--layouts <path>` | 工程2の `layouts.jsonl` を参照し layout_hint 候補を算出する | 指定なし |
| `--draft-output <dir>` | ドラフト成果物の出力先 | `.pptx/draft` |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 | 無効 |
| `--verbose` | 追加ログを表示する | 無効 |

## 生成物とログの設計メモ
- `analysis_snapshot.json`: `--emit-structure-snapshot` 利用時に生成されるアンカー構造スナップショット。
- `brief_cards.json` / `brief_log.json` / `brief_ai_log.json`: ブリーフ正規化工程で作成されるカード本体・HITL ログ・生成ログ。
- `ai_generation_meta.json`: ブリーフ生成の統計・入力ハッシュ・ポリシー情報。
- `brief_story_outline.json`: 章テンプレートとカードの対応を示すアウトライン。
- `audit_log.json`（.brief 配下）: ブリーフ成果物の監査情報。
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
