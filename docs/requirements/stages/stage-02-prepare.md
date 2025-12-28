# stage 2 Prepare 要件詳細

## 概要
- プレペア入力を PrepareCard へ正規化し、stage 3 で直接利用できる JSON 群を `.pptx/prepare/` に出力する。
- 生成 AI の骨子指示は Blueprint や入力メタデータから導出しつつ、人による承認・差戻しの記録を残す。
- 監査証跡と再現性を担保するため、生成結果・統計・成果物パスを `audit_log.json` にまとめる。

## 入力
- Markdown / JSON 形式のプレペア資料（CLI では位置引数で指定）。
- スペースまたはカンマ区切りで複数の PREPARE_PATH を指定でき、JSON/JSONC/Markdown/TXT は構造化入力として統合し、PDF・URL・data URI は ContentImportService でテキスト化する。
- （任意）カード生成枚数 (`-p/--page-limit`)。

## 出力
- `prepare_card.json`: テンプレート非依存のスライド下書き。各カードは `card_id` / `order` / `role.story_phase`（任意）/ `role.intent_tags` と、`content` セクション（`title` または `headline` のどちらか一方、`subtitle`、`body`、`notes`）で構成する。`title` はタイトルページ専用であり、通常スライドでは `headline` のみを保持する。`subtitle` は章名やまとまり表示に利用し、`body` は `type` 付きブロック（例: `paragraph` / `bullets` / `table` / `media`）配列として PowerPoint 本文を表現する。`notes` はノート欄に転記する補足情報として利用する。
- `prepare_log.json`: 承認・差戻し操作の履歴（手動更新時に追記）。
- `prepare_ai_log.json`: 生成 AI の呼び出しログ。モデル名、プロンプトテンプレート、警告、トークン使用量を含む。
- 動的モードでは呼び出しを 1 回に集約し、`prepare_ai_log.json` にはバッチ単位のレコードを出力する。
- `ai_generation_meta.json`: ポリシー ID（内製化後は `null`）、入力ハッシュ、カードごとの `content_hash`・`story_phase`・意図タグ・行数、統計値、`mode`（`dynamic` / `static`）、静的モード時は Blueprint 情報（`blueprint_path` / `blueprint_hash` / `slot_coverage`）、および取り込んだソース一覧 `import_sources`。
- `prepare_story_outline.json`: 章 ID とカード ID の対応表。stage 3 の章構成初期化に利用する。
- `audit_log.json`: 生成時刻、ポリシー ID、成果物パス、実行モード、Blueprint 参照、統計値（必須 slot 充足率など）、`slot_summary`、`import_sources`。

## 業務フロー
1. CLI がプレペア入力（複数指定可）を読み込み、JSON/Markdown/TXT は `PrepareSourceDocument` へパースし、PDF・URL・data URI は ContentImportService でテキスト化した上で章へ変換する。Markdown の見出しや箇条書きはカード候補に変換される。
2. `PrepareAIOrchestrator` がポリシー定義を評価し、カードを生成。生成枚数は `-p/--page-limit` が指定されていない限りポリシーまたは LLM 任せで、動的モードかつページ指定が無い場合はタイトルページ（`content.title` を持つカード）を自動挿入する。`--page-limit` を指定した場合はタイトルページを追加しない。
3. 生成結果を Pydantic モデルで検証し、`prepare_card.json` と関連ログファイルを出力する。
4. 監査ログ (`audit_log.json`) に成果物パスと統計情報を記録する。ハッシュを保持し、改ざん検知に利用できる。
5. stage 3 `pptx compose` は `--prepare-cards` でカード成果物を受け取り、`prepare_card.json.meta` に記録されたログ／AIメタ／アウトラインのパスを自動解決して章構成とマッピングを実行する。compose 以降は新スキーマに沿って本文ブロックをテンプレートへ配置する。

## 監査・品質要件
- 生成 AI が警告を返した場合は `prepare_ai_log.json.warnings` に記録し、CLI 標準出力にも WARN を表示する。
- `ai_generation_meta.json.statistics.cards_total` と `prepare_card.json.cards.length` が一致すること。
- `ai_generation_meta.json.mode` と `audit_log.json.prepare_normalization.mode` が一致し、後 stage で参照できるように保持すること。
- 入力プレペアのハッシュ (`input_hash`) は `audit_log.json` と `ai_generation_meta.json` の両方で整合させる。
- 取り込んだソース情報は `ai_generation_meta.json.import_sources` と `audit_log.json.prepare_normalization.import_sources` の両方に記録し、件数やハッシュ値が一致すること。

## CLI 要件
- `pptx prepare <PREPARE_PATH …>` は入力が解決できない場合に exit code 2 を返す。
- `--mode` オプション（`dynamic` / `static`）を必須とし、実行モード未指定の場合は CLI がエラーで終了する。
- 静的モード (`--mode=static`) では `jobspec.meta.template_spec_path` を参照して Blueprint を読み込む。`--jobspec` 未指定時は `.pptx/template/jobspec.json` を探索し、見つからない場合はエラーにする。
- 動的モードで `-p/--page-limit` を指定しない場合はタイトルページ（`content.title` を持つカード）を自動的に 1 枚追加する。タイトルページを抑止したい場合は `-p/--page-limit` を明示し、ユーザー側でページ数を固定する。
- 参照した Blueprint パスは `ai_generation_meta.json.blueprint_path` と監査ログに記録する。
- 生成結果は `.pptx/prepare/` 配下へ出力し、ディレクトリが存在しない場合は自動生成する。
- `-p/--page-limit` を指定した場合、生成枚数が制限値を超えた際に WARN を出力してリストをトリムする。
- `--output` を指定して別ディレクトリへ書き込む際もファイル構成（`prepare_card.json` 等）は変えない。
- 取り込んだソースのメタ情報は `ai_generation_meta.json.import_sources` と `audit_log.json.prepare_normalization.import_sources` に書き出す。

## 静的モード固有要件
- Blueprint 内の必須 slot (`required=true`) は stage 2 でカードを生成する際に必ず割当し、未割当がある場合は exit code 6 を返す。
- Blueprint の `slide_id` 順にカードを出力し、`prepare_card.json.cards[*].slot_id` で slot を一意に識別できるようにする。
- `ai_generation_meta.json.statistics` に `required_slot_total` / `required_slot_fulfilled` / `optional_slot_used` を追記し、監査ログ `audit_log.json.prepare_normalization.slot_summary` と整合させる。
- Blueprint が指定されても `--mode=dynamic` の場合は従来どおりの動作とし、slot 情報は出力しない。
- `jobspec.meta.template_spec_path` が欠落している場合はテンプレ抽出を再実行するようエラー案内する。
- `--mode=static` 選択時は `--page-limit` を併用できない。
