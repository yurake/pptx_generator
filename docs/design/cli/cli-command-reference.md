# CLI コマンド設計ガイド

## 目的
- CLI の各コマンドが 4 stage パイプラインのどこに位置づくかを整理し、責務や成果物、主要オプションを設計観点でまとめる。
- README のクイックスタートで触れ切れない詳細設定（Polisher・PDF 連携・AI プロバイダー切り替え等）を参照できるようにする。

## ログレベル制御
- 環境変数 `LOG_LEVEL`（`debug` / `info` / `warning` / `error` / `critical` または数値）を設定すると、CLI 全体の標準出力ログレベルを一括で切り替えられる。  
- コマンドラインの `--verbose`（INFO）および `--debug`（DEBUG）が指定された場合はそちらを優先する。  
- 旧環境変数 `OPENAI_LOG` は廃止したため、設定が残っている場合は警告を出して無視する。OpenAI SDK 含む関連ロガーも `LOG_LEVEL` に追従する。

## パイプライン全体像
- パイプラインは「テンプレ → コンテンツ準備 → マッピング（HITL + 自動）→ レンダリング」の 4 stage で構成される。
- `pptx compose` は stage 3（マッピング）を連続実行するラッパーで、HITL 承認から `generate_ready.json` 出力までを一括で処理する。
- `pptx gen` は stage 4（レンダリング）を担当し、stage 3 で生成した `generate_ready.json` を入力に最終成果物（PPTX／PDF）と監査メタを出力する。

### stage 1: テンプレ
テンプレートの整備・抽出・検証・リリースメタ生成を一括で実行する。

#### `pptx template`
| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<template.pptx>` | 解析するテンプレート | ✅ | ✅ | - |
| `--output <dir>` | 抽出・検証成果物を保存するディレクトリ |  |  | `.pptx/extract` |
| `--layout <keyword>` | レイアウト名（前方一致）で抽出対象を絞る |  |  | 全レイアウト |
| `--anchor <keyword>` | アンカー名（前方一致）で抽出対象を絞る |  |  | 全アンカー |
| `--format <json\|yaml>` | テンプレ仕様の出力形式 |  |  | `json` |
| `--layout-mode <dynamic\|static>` | テンプレ運用モード。`static` で Blueprint を出力 |  |  | `dynamic` |
| `--with-release` | リリースメタ（`template_release.json` 等）を生成する |  |  | 無効 |
| `--brand <name>` | `--with-release` 指定時のブランド名 |  |  | - |
| `--version <value>` | `--with-release` 指定時のテンプレバージョン |  |  | - |
| `--template-id <value>` | リリース ID。未指定時は `<brand>_<version>` |  |  | 自動生成 |
| `--release-output <dir>` | リリース成果物の出力先 |  |  | `.pptx/release` |
| `--generated-by / --reviewed-by` | リリースメタに記録する担当者 |  |  | 空 |
| `--baseline-release <path>` | 過去の `template_release.json` と比較する |  |  | 指定なし |
| `--golden-spec <spec.json>` | ゴールデンサンプル検証に用いる spec（複数指定可） |  |  | 指定なし |

オプションを省略した場合は、抽出結果が既定の `.pptx/extract/` 配下に出力される。例えば以下のようにテンプレートファイルのみを指定すれば、最小構成で抽出と検証が実行できる。

```bash
uv run pptx template samples/templates/templates.pptx
```

主要成果物:
- `.pptx/extract/template_spec.json` / `template_spec.yaml`
- `.pptx/extract/jobspec.json`
- `.pptx/extract/branding.json`
- `.pptx/extract/layouts.jsonl`
- `.pptx/extract/diagnostics.json`（`diff_report.json` は比較時のみ）
- `--with-release` 指定時は `.pptx/release/` に `template_release.json`, `release_report.json`, `golden_runs.json`

`pptx template` は抽出完了後にレイアウト検証を自動実行するため、通常は本コマンド単体でテンプレ が完結する。`--layout-mode=static` を指定すると `template_spec.json` に Blueprint (`slides[*].slots[*]`) が含まれ、静的テンプレ運用に必要な `slot_id` 情報を自動生成する。詳細な制御が必要な場合は以下の個別サブコマンドを利用する。

> static モードでテンプレを抽出した場合、`.pptx/extract/prompts/` にスライド単位のプロンプト雛形 (`01_<layout>.md`) と `.pptx/slide_inputs.md` を同時出力する。`<<<user-editable:*>` ブロックのみ編集すると、stage 2 の `pptx prepare --mode static` が自動的に LLM プロンプトへ取り込み、AI ログ (`prepare_ai_log.json`) と `ai_generation_meta.json` に適用結果が記録される。`.pptx/slide_inputs.md` には `01_<layout>` をキーにカード生成時に参照するデータファイルパスを記述できる。

#### 詳細: 個別コマンド

##### `pptx tpl-extract`
`pptx template` の抽出部分のみを実行する。成果物の出力ディレクトリを分けたい場合やフィルタリングを個別に試したい場合に利用する。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `--template <path>` | 解析する `.pptx` テンプレート | ✅ |  | - |
| `--output <dir>` | 抽出結果を保存するディレクトリ |  |  | `.pptx/extract` |
| `--layout <keyword>` | レイアウト名（前方一致）で抽出対象を絞る |  |  | 全レイアウト |
| `--anchor <keyword>` | アンカー名（前方一致）で抽出対象を絞る |  |  | 全アンカー |
| `--format <json\|yaml>` | 出力形式を選択 |  |  | `json` |
| `--layout-mode <dynamic\|static>` | テンプレ運用モード。`static` で Blueprint を出力 |  |  | `dynamic` |

##### `pptx layout-validate`
抽出結果と同等のレイアウト検証を単独で実行する。`--baseline` や `--analyzer-snapshot` を用いて比較条件を変えたいケースで利用する。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `--template <path>` | 検証対象の `.pptx` テンプレート | ✅ |  | - |
| `--output <dir>` | 検証成果物を保存するディレクトリ |  |  | `.pptx/validation` |
| `--template-id <value>` | `layouts.jsonl` に記録するテンプレート ID。未指定時はファイル名から導出 |  |  | 自動導出 |
| `--baseline <path>` | 過去に出力した `layouts.jsonl` と比較し差分を算出する |  |  | 比較なし |
| `--analyzer-snapshot <path>` | `pptx gen --emit-structure-snapshot` が生成した `analysis_snapshot.json` を突合する |  |  | 未指定 |

##### `pptx tpl-release`
テンプレート整備が完了した後、リリースメタのみを生成する場合に利用する。`pptx template --with-release` と同じ成果物構成で、リリースオプションを細かく制御できる。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `--template <path>` | リリース対象のテンプレート | ✅ |  | - |
| `--brand <name>` | ブランド名 | ✅ |  | - |
| `--version <value>` | テンプレートのバージョン | ✅ |  | - |
| `--template-id <value>` | リリース ID。未指定時は `<brand>_<version>` を自動生成 |  |  | 自動生成 |
| `--output <dir>` | リリース成果物の出力先 |  |  | `.pptx/release` |
| `--generated-by <name>` | リリース実施者 |  |  | 空 |
| `--reviewed-by <name>` | レビュー担当者 |  |  | 空 |
| `--baseline-release <path>` | 過去の `template_release.json` と比較する |  |  | 比較なし |
| `--golden-spec <spec.json>` | ゴールデンサンプル検証に用いる spec（複数指定可） |  |  | 指定なし |
| `--layout-mode <dynamic\|static>` | テンプレ運用モード。`static` で Blueprint を出力 |  |  | `dynamic` |

### stage 2: コンテンツ準備 (HITL)
プレペア入力（Markdown / JSON など）を PrepareCard モデルに整形し、HITL でレビューしながら `.pptx/prepare/` 配下へ成果物一式を出力する。生成内容は stage 3 のドラフト構築・マッピングで直接参照される。

#### `pptx prepare`
- `--mode` でテンプレ運用モードを明示する。`dynamic` は従来どおりテンプレ依存なしでカードを生成し、`static` は Blueprint を参照して slot 単位のカードを生成する。
- 静的モードでは `jobspec.meta.template_spec_path` に記録された Blueprint を参照する。`jobspec` が見つからない場合は `.pptx/extract/jobspec.json` を自動探索し、`--jobspec` で明示指定も可能。`--mode=static` と `--page-limit` の併用はできない。
- `.pptx/slide_inputs.md` を用意するとスライドごとに入力データを指定でき、全スライド分が記載されていれば `<prepare_path>` 引数を省略できる。未指定スライドがある場合はエラー。
- 生成カード枚数を制御したい場合は `-p/--page-limit` を利用する。`--output` で成果物ディレクトリを変更できる。
- static モードで `.pptx/extract/prompts/` 配下の Markdown を編集すると、該当スライドの user-editable 節が LLM プロンプトへ注入される（雛形は `pptx template` 実行時に自動生成され、未編集ファイルは既定プロンプトを保持する）。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<prepare_source.txt>` | プレペア入力ファイル | ✅ | ✅ | - |
| `--output <dir>` | 生成物を保存するディレクトリ |  |  | `.pptx/prepare` |
| `--mode <dynamic\|static>` | 生成モードを指定する | ✅ |  | - |
| `--jobspec <path>` | `jobspec.json` を指定（template_spec_path を参照） | 静的モードで ✅ |  | `.pptx/extract/jobspec.json` を探索 |
| `-p/--page-limit <int>` | 生成するカード枚数の上限 |  |  | 指定なし |

実行例:
```bash
uv run pptx prepare samples/contents/sample_import_content_summary.txt \
  --mode dynamic \
  --output .pptx/prepare
```

生成物（例）:
- `prepare_card.json`: PrepareCard 配列（静的モード時は `slide_id` / `slot_id` / `required` / `layout_mode` を含む）
- `prepare_log.json`: 承認・差戻しイベントログ（初回は空配列）
- `prepare_ai_log.json`: 生成 AI との対話ログ
- `ai_generation_meta.json`: 生成統計・入力ハッシュ・モード情報・Blueprint 参照
- `prepare_story_outline.json`: 章構成とカード紐付け
- `audit_log.json`: stage 2 の監査メタ情報（静的モード時は slot 充足率・Blueprint パスを記録）
- カード承認ステータスは CLI では変更できない。HITL 承認は PrepareStore / API を通じて行い、その結果が `prepare_log.json` とストア内の状態へ記録される。stage 3 へ進む際は最新ログまたはストアエクスポート結果を参照させること。
### stage 3: マッピング (HITL + 自動)
章構成の承認とレイアウト割付をまとめて実行し、`generate_ready.json`・`generate_ready_meta.json`・`draft_review_log.json`・`draft_mapping_log.json` を整備する。Prepare 成果物を必須入力とし、HITL 差戻しや再実行時も出力ディレクトリを固定できる。

#### 推奨: `pptx compose`
- stage 3 全体を一括で実行し、`.pptx/draft/` にドラフト成果物、`.pptx/compose/` に `generate_ready.json`・`generate_ready_meta.json`・`draft_mapping_log.json` を生成する。
- `--prepare-cards` で stage 2 の成果物を指定すると、CLI が `prepare_card.json.meta` に記録されたパスを使ってログや AI メタを読み込む。
- 承認状態（差戻し含む）は PrepareStore の管理下にあり、CLI は読み取りのみを行う。
- `jobspec.meta.template_path` と `jobspec.meta.layouts_path` を必ず埋め込む。欠落している場合はエラーになる。
- ドラフトボードの永続化データは `.pptx/draft/store/` に保存され、環境変数 `DRAFT_STORE_DIR` で上書きできる。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<jobspec.json>` | Stage1 で生成したジョブスペック | ✅ | ✅ | - |
| `--prepare-cards <path>` | stage 2 の `prepare_card.json` | ✅ |  | `.pptx/prepare/prepare_card.json` |
| `--draft-output <dir>` | ドラフト成果物の保存先 |  |  | `.pptx/draft` |
| `--generate-ready-filename <name>` | `generate_ready.json` のファイル名 |  |  | `generate_ready.json` |
| `--generate-ready-meta <name>` | `generate_ready_meta.json` のファイル名 |  |  | `generate_ready_meta.json` |
| `--review-log-filename <name>` | `draft_review_log.json` のファイル名 |  |  | `draft_review_log.json` |
| `--mapping-log-filename <name>` | `draft_mapping_log.json` のファイル名 |  |  | `draft_mapping_log.json` |
| `--target-length`, `--structure-pattern`, `--appendix-limit` | chapter API のチューニング |  |  | Spec から推定 |
| `--chapter-templates-dir` / `--chapter-template` | 章テンプレート辞書／テンプレート ID |  |  | `config/chapter_templates` / 自動推定 |
| `--import-analysis <path>` | `analysis_summary.json` を取り込み補助情報を活用する |  |  | 指定なし |
| `--show-layout-reasons` | layout_hint スコアの内訳を標準出力に表示する |  |  | 無効 |
| `--rules <path>` | マッピング時に参照するルール設定 |  |  | `config/rules.json` |
| `--branding <path>` | ブランド設定ファイルを明示指定する |  |  | `config/branding.json` |

> ※ jobspec の `meta` に `template_path` / `layouts_path` が含まれていることが前提です（CLI 側で必須チェックを行います）。

#### 補助: `pptx outline`
- HITL 作業（章構成確認）だけを個別に実行したい場合に利用し、`generate_ready.json` と関連メタ／ログを再生成する。
- `--prepare-cards` を指定すると `prepare_card.json.meta` のパスからログ／AIメタを自動解決する。差戻し対応や一部章のみ更新したいケースで活用する。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<jobspec.json>` | Stage1 で生成したジョブスペック（位置引数） | ✅ | ✅ | - |
| `--prepare-cards <path>` | stage 2 の `prepare_card.json` | ✅ |  | `.pptx/prepare/prepare_card.json` |
| `--output <dir>` | ドラフト成果物を保存するディレクトリ |  |  | `.pptx/draft` |
| `--target-length`, `--structure-pattern`, `--appendix-limit` | chapter API のチューニング |  |  | Spec から推定 / 5 |
| `--chapter-templates-dir` / `--chapter-template` | 章テンプレート辞書／テンプレート ID |  |  | `config/chapter_templates` / 自動推定 |
| `--import-analysis <path>` | `analysis_summary.json` を取り込み補助情報を活用する |  |  | 指定なし |
| `--return-reasons-path <path>` | 差戻し理由テンプレート辞書のパス |  |  | `config/return_reasons.json` |
| `--return-reasons` | 差戻し理由テンプレート一覧を表示して終了する |  |  | 無効 |
| `--show-layout-reasons` | layout_hint スコアの内訳を標準出力に表示する |  |  | 無効 |

#### 補助: `pptx mapping`
- stage 4（レンダリング）で利用する。`generate_ready.json` とテンプレートを入力に PPTX を生成し、旧 `draft_*` ファイルには依存しない。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<jobspec.json>` | Stage1 で生成したジョブスペック（位置引数） | ✅ | ✅ | - |
| `--prepare-cards <path>` | stage 2 の `prepare_card.json` | ✅ |  | `.pptx/prepare/prepare_card.json` |
| `--output <dir>` | generate_ready 等の出力ディレクトリ |  |  | `.pptx/gen` |
| `--rules <path>` | 検証ルール設定ファイル |  |  | `config/rules.json` |
| `--draft-output <dir>` | draft 成果物の出力先 |  |  | `.pptx/draft` |
| `--branding <path>` | ブランド設定ファイル |  |  | `config/branding.json` |

> ※ jobspec の `meta` に `template_path` / `layouts_path` を必ず設定する。CLI はこれらのメタ情報からパスを解決し、欠落時はエラーになる。
### stage 4: レンダリング
最終成果物（PPTX/PDF）と監査ログを生成する。

#### `pptx gen`
- `generate_ready.json` を入力に stage 4 を実行する。テンプレートパスは `meta.template_path` から自動解決され、LibreOffice・Polisher などの周辺処理も同時に実行される。
- `--branding` を省略した場合はテンプレートからの抽出結果または既定ブランドを使用する。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<generate_ready.json>` | generate_ready ドキュメント | ✅ | ✅ | - |
| `--output <dir>` | 生成物を保存するディレクトリ |  |  | `.pptx/gen` |
| `--pptx-name <filename>` | 出力 PPTX 名を変更する |  |  | `proposal.pptx` |
| `--rules <path>` | Analyzer / Polisher 設定に利用するルールファイル |  |  | `config/rules.json` |
| `--branding <path>` | ブランド設定 JSON を差し替える |  |  | `config/branding.json` |
| `--export-pdf` | LibreOffice 経由で PDF を同時生成 |  |  | 無効 |
| `--pdf-mode <both\|only>` | PDF のみ出力するかを選択 |  |  | `both` |
| `--pdf-output <filename>` | 出力 PDF 名を変更する |  |  | `proposal.pdf` |
| `--libreoffice-path <path>` | `soffice` のパスを明示する |  |  | `PATH` から探索 |
| `--pdf-timeout <sec>` | LibreOffice 実行のタイムアウト秒 |  |  | 120 |
| `--pdf-retries <count>` | PDF 変換のリトライ回数 |  |  | 2 |
| `--polisher/--no-polisher` | Polisher の明示的な有効化／無効化 |  |  | 設定ファイル準拠 |
| `--polisher-path <path>` | Polisher 実行ファイルのパス |  |  | 指定なし |
| `--polisher-rules <path>` | Polisher のルール設定 |  |  | 指定なし |
| `--polisher-timeout <sec>` | Polisher のタイムアウト秒 |  |  | 指定なし |
| `--polisher-arg <value>` | Polisher へ渡す追加引数（複数指定可） |  |  | 指定なし |
| `--polisher-cwd <dir>` | Polisher 実行時のカレントディレクトリ |  |  | 指定なし |
| `--emit-structure-snapshot` | Analyzer の構造スナップショットを出力する |  |  | 無効 |
| `--polisher-path <path>` | Polisher 実行ファイル（`.exe` / `.dll` 等）を明示する |  |  | `config/rules.json` の `polisher.executable` または環境変数 |
| `--polisher-rules <path>` | Polisher 用ルール設定ファイルを差し替える |  |  | `config/rules.json` の `polisher.rules_path` |
| `--polisher-timeout <sec>` | Polisher 実行のタイムアウト秒数 |  |  | `polisher.timeout_sec` |
| `--polisher-arg <value>` | Polisher に追加引数を渡す（複数指定可 / `{pptx}`, `{rules}` プレースホルダー対応） |  |  | 指定なし |
| `--polisher-cwd <dir>` | Polisher 実行時のカレントディレクトリを固定する |  |  | カレントディレクトリ |
| `--verbose` | 追加ログを表示する |  |  | 無効 |

#### `pptx gen`
- stage 3 で生成した `generate_ready.json` を入力に、stage 4 のレンダリング・Polisher・PDF 変換を実行するコマンド。
- `generate_ready.json.meta.template_path` からテンプレートを解決するため、`--template` オプションは存在しない。テンプレート情報が欠落している場合は CLI がエラーで停止し、再マッピングを促す。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<generate_ready.json>` | レンダリング対象の generate_ready | ✅ | ✅ | - |
| `--branding <path>` | ブランド設定 JSON を差し替える |  |  | `config/branding.json` |
| `--rules <path>` | 文字数や段落レベル制限を定義したルールを指定 |  |  | `config/rules.json` |
| `--output <dir>` | 生成物を保存するディレクトリ |  |  | `.pptx/gen` |
| `--pptx-name <filename>` | 出力 PPTX 名を変更する |  |  | `proposal.pptx` |
| `--export-pdf` | LibreOffice 経由で PDF を同時生成 |  |  | 無効 |
| `--pdf-mode <both\|only>` | PDF のみ出力するかを選択 |  |  | `both` |
| `--pdf-output <filename>` | 出力 PDF 名を変更する |  |  | `proposal.pdf` |
| `--libreoffice-path <path>` | `soffice` のパスを明示する |  |  | `PATH` から探索 |
| `--pdf-timeout <sec>` | LibreOffice 実行のタイムアウト秒数 |  |  | 120 |
| `--pdf-retries <count>` | PDF 変換のリトライ回数 |  |  | 2 |
| `--polisher/--no-polisher` | Open XML Polisher を実行するかを指定 |  |  | ルール設定の値 |
| `--polisher-path <path>` | Polisher 実行ファイルを明示する |  |  | `config/rules.json` の `polisher.executable` または環境変数 |
| `--polisher-rules <path>` | Polisher 用ルール設定ファイルを差し替える |  |  | `config/rules.json` の `polisher.rules_path` |
| `--polisher-timeout <sec>` | Polisher 実行のタイムアウト秒数 |  |  | `polisher.timeout_sec` |
| `--polisher-arg <value>` | Polisher に追加引数を渡す（複数指定可 / `{pptx}` `{rules}` プレースホルダー対応） |  |  | 指定なし |
| `--polisher-cwd <dir>` | Polisher 実行時のカレントディレクトリを固定する |  |  | カレントディレクトリ |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 |  |  | 無効 |
| `--verbose` | 追加ログを表示する |  |  | 無効 |

## 生成物とログの設計メモ
- `prepare_card.json` / `prepare_log.json` / `prepare_ai_log.json` / `ai_generation_meta.json` / `prepare_story_outline.json`: stage 2 で生成される Prepare 成果物。
- `generate_ready.json`: マッピング stage で確定したレイアウトとプレースホルダー割付。
- `draft_mapping_log.json`: レイアウト候補スコア、フォールバック履歴、Analyzer 指摘サマリ。
- `fallback_report.json`: フォールバック発生スライドの一覧（発生時のみ）。
- `generate_ready_meta.json`: 章テンプレ適合率、承認統計、Analyzer サマリ、監査メタ。
- `draft_review_log.json`: HITL 操作ログ。
- `rendering_log.json`: レンダリング監査結果（検出要素・警告コード・空プレースホルダー件数）。
- `monitoring_report.json`: Analyzer/レンダリングの警告件数サマリ。
- `analysis.json` / `review_engine_analyzer.json`: レンダリング結果の解析・レビュー用メタ。
- `analysis_snapshot.json`: `--emit-structure-snapshot` 利用時に生成されるアンカー構造スナップショット。
- `outputs/audit_log.json`: 生成時刻や成果物ハッシュ、PDF/Polisher のメタ情報。
- `branding.json`: テンプレ抽出時に `.pptx/extract/` へ保存されるブランド設定。


## 運用上のポイント
- Polisher を有効化する場合は .NET 8 SDK を導入し、`config/rules.json` の `polisher` 設定と整合させる。
- PDF 変換機能を利用する場合は LibreOffice (headless 実行可能) を導入し、`soffice --headless --version` で動作確認する。
- CLI オプションの変更に伴う運用手順は `docs/runbooks/` を更新し、ToDo へメモを残す。
