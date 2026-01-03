# CLI コマンド設計ガイド

## 目的
- CLI の各コマンドが 4 stage パイプラインのどこに位置づくかを整理し、責務や成果物、主要オプションを設計観点でまとめる。
- README のクイックスタートで触れ切れない詳細設定（Polisher・PDF 連携・AI プロバイダー切り替え等）を参照できるようにする。

## ログレベル制御
- 環境変数 `LOG_LEVEL`（`debug` / `info` / `warning` / `error` / `critical` または数値）を設定すると、CLI 全体の標準出力ログレベルを一括で切り替えられる。  
- コマンドラインの `--verbose`（INFO）および `--debug`（DEBUG）が指定された場合はそちらを優先する。  

## パイプライン全体像
- パイプラインは「テンプレ → コンテンツ準備 → マッピング（HITL + 自動）→ レンダリング」の 4 stage で構成される。
- `pptx compose` は stage 3（マッピング）を連続実行するラッパーで、HITL 承認から `generate_ready.json` 出力までを一括で処理する。
- `pptx gen` は stage 4（レンダリング）を担当し、stage 3 で生成した `generate_ready.json` を入力に最終成果物（PPTX／PDF）と監査メタを出力する。
- Stage5（編集反映）向けに `pptx edit` を用意。Stage4 生成済み PPTX と差分 JSON（`shape_id`, `edit`, `contents`）を入力し、書式を保持したままテキスト差し替えを行う。位置引数で PPTX を指定し、`--edits-json`（または `--edits` 直接指定）が無い場合は LLM で差分を生成して適用する。
- 出力ルートは `PPTX_OUTPUT_ROOT` で切り替えられる（未指定は `.pptx/<stage>`）。API/Web では `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` 規約を前提とする。
- 入力ルートは Web/API 専用で `PPTX_INPUT_ROOT/<transaction_id>/<job_id>/` を利用する（未指定は `.pptx/input`）。CLI 既定の入力パスは従来どおりで変更しない。
- CLI は内部的にメモリキュー＋ワーカーを用いるが、実行完了まで待機する同期挙動を維持する。API/Web は同一プロセス内の複数ワーカーで非同期実行を前提とし、ジョブ状態の永続化は行わない（必要ならクライアント側で保持）。

### stage 1: テンプレ
テンプレートの整備・抽出・検証・リリースメタ生成を一括で実行する。

#### `pptx template`
| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<template.pptx>` | 解析するテンプレート | ✅ | ✅ | - |
| `--output <dir>` | 抽出・検証成果物を保存するディレクトリ |  |  | `.pptx/template` |
| `--layout <keyword>` | レイアウト名（前方一致）で抽出対象を絞る |  |  | 全レイアウト |
| `--anchor <keyword>` | アンカー名（前方一致）で抽出対象を絞る |  |  | 全アンカー |
| `--format <json\|yaml>` | テンプレ仕様の出力形式 |  |  | `json` |
| `--mode <dynamic\|static>` | テンプレ運用モード。`static` で Blueprint を出力 |  |  | `dynamic` |
| `--from <slide\|template>` | 静的モード時に抽出へ利用するソースを指定。既定は実スライド |  |  | `slide` |
| `--slide` | 実スライドの図形・段落スナップショット (`slide_snapshot.json`) を出力する |  |  | 無効 |
| `--with-release` | リリースメタ（`template_release.json` 等）を生成する |  |  | 無効 |
| `--brand <name>` | `--with-release` 指定時のブランド名 |  |  | - |
| `--version <value>` | `--with-release` 指定時のテンプレバージョン |  |  | - |
| `--template-id <value>` | リリース ID。未指定時は `<brand>_<version>` |  |  | 自動生成 |
| `--release-output <dir>` | リリース成果物の出力先 |  |  | `.pptx/release` |
| `--generated-by / --reviewed-by` | リリースメタに記録する担当者 |  |  | 空 |
| `--baseline-release <path>` | 過去の `template_release.json` と比較する |  |  | 指定なし |
| `--golden-spec <spec.json>` | ゴールデンサンプル検証に用いる spec（複数指定可） |  |  | 指定なし |

オプションを省略した場合は、抽出結果が既定の `.pptx/template/` 配下に出力される。例えば以下のようにテンプレートファイルのみを指定すれば、最小構成で抽出と検証が実行できる。

```bash
uv run pptx template samples/templates/templates.pptx
```

主要成果物:
- `.pptx/template/template_spec.json` / `template_spec.yaml`
- `.pptx/template/jobspec.json`
- `.pptx/template/branding.json`（テンプレートから抽出したスタイルスナップショット。運用メモ用途）
- `.pptx/template/layouts.jsonl`
- `.pptx/template/diagnostics.json`（`diff_report.json` は比較時のみ）
- `.pptx/template/slide_snapshot.json`（`--slide` 指定時。図形寸法・z-order・回転・プレースホルダー種別、各段落のフォント・整列・インデント・行間など実スライドの実体データを集約）
- `--with-release` 指定時は `.pptx/release/` に `template_release.json`, `release_report.json`, `golden_runs.json`

`pptx template` は抽出完了後にレイアウト検証を自動実行するため、通常は本コマンド単体でテンプレ が完結する。`--mode=static` を指定すると `template_spec.json` に Blueprint (`slides[*].slots[*]`) が含まれ、静的テンプレ運用に必要な `slot_id` 情報を自動生成する。詳細な制御が必要な場合は以下の個別サブコマンドを利用する。

> static モードでテンプレを抽出した場合、`.pptx/template/prompts/` にスライド単位のプロンプト雛形 (`01_<layout>.md`) と `.pptx/slide_inputs.md` を同時出力する。`<<<user-editable:*>` ブロックのみ編集すると、stage 2 の `pptx prepare --mode static` が自動的に LLM プロンプトへ取り込み、AI ログ (`prepare_ai_log.json`) と `ai_generation_meta.json` に適用結果が記録される。`.pptx/slide_inputs.md` には `01_<layout>` をキーにカード生成時に参照するデータファイルパスを記述できる。

#### 詳細: 個別コマンド

##### `pptx tpl-extract`
`pptx template` の抽出部分のみを実行する。成果物の出力ディレクトリを分けたい場合やフィルタリングを個別に試したい場合に利用する。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `--template <path>` | 解析する `.pptx` テンプレート | ✅ |  | - |
| `--output <dir>` | 抽出結果を保存するディレクトリ |  |  | `.pptx/template` |
| `--layout <keyword>` | レイアウト名（前方一致）で抽出対象を絞る |  |  | 全レイアウト |
| `--anchor <keyword>` | アンカー名（前方一致）で抽出対象を絞る |  |  | 全アンカー |
| `--format <json\|yaml>` | 出力形式を選択 |  |  | `json` |
| `--layout-mode <dynamic\|static>` | テンプレ運用モード。`static` で Blueprint を出力 |  |  | `dynamic` |
| `--from <slide\|template>` | 静的モード時に抽出へ利用するソースを指定 |  |  | `slide` |

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
- 静的モードでは `jobspec.meta.template_spec_path` に記録された Blueprint を参照する。`jobspec` が見つからない場合は `.pptx/template/jobspec.json` を自動探索し、`--jobspec` で明示指定も可能。`--mode=static` と `--page-limit` の併用はできない。
- `.pptx/slide_inputs.md` を用意するとスライドごとに入力データを指定でき、全スライド分が記載されていれば `<prepare_path>` 引数を省略できる。未指定スライドがある場合はエラー。
- `<PREPARE_PATH>` はスペースまたはカンマ区切りで複数指定できる。JSON/JSONC/Markdown/TXT は構造化入力として結合し、PDF・URL・data URI は ContentImportService でテキスト化したうえで章へ変換する。
- 生成カード枚数を制御したい場合は `-p/--page-limit` を利用する。`--output` で成果物ディレクトリを変更できる。
- 取り込んだソースは `ai_generation_meta.json.import_sources` と `audit_log.json.prepare_normalization.import_sources` に記録され、後続ステージや監査で参照できる。
- static モードで `.pptx/template/prompts/` 配下の Markdown を編集すると、該当スライドの user-editable 節が LLM プロンプトへ注入される（雛形は `pptx template` 実行時に自動生成され、未編集ファイルは既定プロンプトを保持する）。
- CLI 実装では `resolve_static_context` が jobspec・Blueprint・slide_inputs を正規化し、`PrepareCommandArtifacts` が `prepare_card.json` など成果物の一括書き出しを担う。外部モジュールからも同 API を利用できるため、GUI やバッチスクリプトからの再利用が容易になっている。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<PREPARE_PATH …>` | プレペア入力。スペース/カンマ区切りで複数指定可（JSON/JSONC/Markdown/TXT/PDF/URL/data URI） | Dynamic モードで ✅ | ✅ | - |
| `--output <dir>` | 生成物を保存するディレクトリ |  |  | `.pptx/prepare` |
| `--mode <dynamic\|static>` | 生成モードを指定する | ✅ |  | - |
| `--jobspec <path>` | `jobspec.json` を指定（template_spec_path を参照） | 静的モードで ✅ |  | `.pptx/template/jobspec.json` を探索 |
| `-p/--page-limit <int>` | 生成するカード枚数の上限 |  |  | 指定なし |

実行例:
```bash
uv run pptx prepare samples/input/pitch.md \
  --mode dynamic \
  --output .pptx/prepare
```

複数ソースをまとめて取り込む例:
```bash
uv run pptx prepare notes/brief.md https://example.com/report.pdf \
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
- stage 3 全体を一括で実行し、`--output` で指定したディレクトリに `generate_ready.json`・`generate_ready_meta.json`・`draft_mapping_log.json` を生成する。ドラフト関連ログは `<output>/draft/` 配下へ出力される。
- `--prepare-cards` で stage 2 の成果物を指定すると、CLI が `prepare_card.json.meta` に記録されたパスを使ってログや AI メタを読み込む。
- 承認状態（差戻し含む）は PrepareStore の管理下にあり、CLI は読み取りのみを行う。
- `jobspec.meta.template_path` と `jobspec.meta.layouts_path` を必ず埋め込む。欠落している場合はエラーになる。
- ドラフトボードの永続化データは `<output>/draft/store/` に保存され、環境変数 `DRAFT_STORE_DIR` で上書きできる（既定の `--output` 利用時は `.pptx/compose/draft/store/`）。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<jobspec.json>` | Stage1 で生成したジョブスペック | ✅ | ✅ | - |
| `--prepare-cards <path>` | stage 2 の `prepare_card.json`。省略時は `.pptx/prepare/prepare_card.json` を探索し、存在しなければエラー |  |  | `.pptx/prepare/prepare_card.json` |
| `--generate-ready-filename <name>` | `generate_ready.json` のファイル名 |  |  | `generate_ready.json` |
| `--generate-ready-meta <name>` | `generate_ready_meta.json` のファイル名 |  |  | `generate_ready_meta.json` |
| `--review-log-filename <name>` | `draft_review_log.json` のファイル名 |  |  | `draft_review_log.json` |
| `--mapping-log-filename <name>` | `draft_mapping_log.json` のファイル名 |  |  | `draft_mapping_log.json` |
| `--target-length`, `--structure-pattern`, `--appendix-limit` | chapter API のチューニング |  |  | Spec から推定 |
| `--import-analysis <path>` | `analysis_summary.json` を取り込み補助情報を活用する |  |  | 指定なし |
| `--show-layout-reasons` | layout_hint スコアの内訳を標準出力に表示する |  |  | 無効 |
| `--rules <path>` | マッピング時に参照するルール設定 |  |  | `src/pptx_generator/config/pipeline_rules.json` |

> ※ jobspec の `meta` に `template_path` / `layouts_path` が含まれていることが前提です（CLI 側で必須チェックを行います）。

#### 補助: `pptx outline`
- HITL 作業（章構成確認）だけを個別に実行したい場合に利用し、`generate_ready.json` と関連メタ／ログを再生成する。
- `--prepare-cards` を指定すると `prepare_card.json.meta` のパスからログ／AIメタを自動解決する。差戻し対応や一部章のみ更新したいケースで活用する。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<jobspec.json>` | Stage1 で生成したジョブスペック（位置引数） | ✅ | ✅ | - |
| `--prepare-cards <path>` | stage 2 の `prepare_card.json`。省略時は `.pptx/prepare/prepare_card.json` を探索し、存在しなければエラー |  |  | `.pptx/prepare/prepare_card.json` |
| `--output <dir>` | ドラフト成果物を保存するディレクトリ |  |  | `.pptx/draft` |
| `--target-length`, `--structure-pattern`, `--appendix-limit` | chapter API のチューニング |  |  | Spec から推定 / 5 |
| `--import-analysis <path>` | `analysis_summary.json` を取り込み補助情報を活用する |  |  | 指定なし |
| `--show-layout-reasons` | layout_hint スコアの内訳を標準出力に表示する |  |  | 無効 |

ドラフト成果物を任意ディレクトリへ分離したい場合は、`--output` を `<root>` に設定したうえで `<root>/draft` を参照する。

#### 補助: `pptx mapping`
- stage 3 のマッピング処理だけを個別実行し、`generate_ready.json` 系とドラフトログを出力する。レンダリングは実行しない。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<jobspec.json>` | Stage1 で生成したジョブスペック（位置引数） | ✅ | ✅ | - |
| `--prepare-cards <path>` | stage 2 の `prepare_card.json` | ✅ |  | `.pptx/prepare/prepare_card.json` |
| `--output <dir>` | generate_ready 等の出力ディレクトリ |  |  | `.pptx/gen` |
| `--rules <path>` | 検証ルール設定ファイル |  |  | `src/pptx_generator/config/pipeline_rules.json` |
| （自動） | draft 成果物の出力先 |  |  | `<output>/draft` |

> ※ jobspec の `meta` に `template_path` / `layouts_path` を必ず設定する。CLI はこれらのメタ情報からパスを解決し、欠落時はエラーになる。

### stage 4: レンダリング
最終成果物（PPTX/PDF）と監査ログを生成する。

#### `pptx gen`
- stage 3 で生成した `generate_ready.json` を入力に、stage 4 のレンダリング・Polisher・PDF 変換を実行するコマンド。
- `generate_ready.json.meta.template_path` からテンプレートを解決するため、`--template` オプションは存在しない。テンプレート情報が欠落している場合は CLI がエラーで停止し、再マッピングを促す。

| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<generate_ready.json>` | レンダリング対象の generate_ready | ✅ | ✅ | - |
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
| `--polisher-rules <path>` | Polisher 用ルール設定ファイルを差し替える |  |  | 指定なし（デフォルトは内蔵ルールを使用） |
| `--polisher-timeout <sec>` | Polisher 実行のタイムアウト秒数 |  |  | `polisher.timeout_sec` |
| `--polisher-arg <value>` | Polisher に追加引数を渡す（複数指定可 / `{pptx}` `{rules}` プレースホルダー対応） |  |  | 指定なし |
| `--polisher-cwd <dir>` | Polisher 実行時のカレントディレクトリを固定する |  |  | カレントディレクトリ |
| `--emit-structure-snapshot` | Analyzer の構造スナップショット (`analysis_snapshot.json`) を生成 |  |  | 無効 |
| `--verbose` | 追加ログを表示する |  |  | 無効 |

### stage 5: 編集反映
生成済み PPTX へテキスト差し替えを適用する。位置引数で PPTX を指定し、`--edits-json` 未指定なら LLM が差分を自動生成して適用する（CLI は `--edits` 直接指定を持たない）。

出力:
- PPTX（書式保持で差し替え済み。差分 JSON は内部保存のみ）

出力先既定:
- CLI: `.pptx/edit/<pptxファイル名>`
- API: `PPTX_OUTPUT_ROOT/<transaction_id>/edit/<job_id>/` 配下に PPTX（JSON は内部保存）

#### `pptx edit`
| オプション | 説明 | 必須 | 位置引数 | 既定値 |
| --- | --- | --- | --- | --- |
| `<pptx_path>` | 差分適用対象の PPTX | ✅ | ✅ | - |
| `--edits-json <path>` | 差分 JSON。指定時は LLM 呼び出しなしで適用のみ |  |  | 指定なし（LLM 自動生成） |
| `--output <path>` | 出力先 PPTX パス |  |  | `.pptx/edit/<pptx名>` |

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
- `generate_ready_meta.json.template_style`: レンダリングや Analyzer が参照するテンプレートスタイルスナップショット。
- `branding.json`: `pptx template` 実行時に出力される参考用スタイル記録（テンプレ設計資料向け）。


## 運用上のポイント
- Polisher を有効化する場合は .NET 8 SDK を導入し、`config/rules.json` の `polisher` 設定と整合させる。
- PDF 変換機能を利用する場合は LibreOffice (headless 実行可能) を導入し、`soffice --headless --version` で動作確認する。
- CLI オプションの変更に伴う運用手順は `docs/runbooks/` を更新し、ToDo へメモを残す。
