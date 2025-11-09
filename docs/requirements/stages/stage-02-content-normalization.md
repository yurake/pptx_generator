# 工程2 コンテンツ準備 (HITL) 要件詳細

## 概要
- ブリーフ入力を BriefCard へ正規化し、工程3 で直接利用できる JSON 群を `.pptx/prepare/` に出力する。
- 生成 AI とポリシー設定を切り替えられるようにしつつ、HITL による承認・差戻しの記録を残す。
- 監査証跡と再現性を担保するため、生成結果・統計・成果物パスを `audit_log.json` にまとめる。

## 入力
- Markdown / JSON 形式のブリーフ資料（CLI では位置引数で指定）。
- 生成 AI ポリシー定義 `config/brief_policies/default.json`。
- （任意）カード生成枚数 (`-p/--page-limit`)。

## 出力
- `prepare_card.json`: カード ID・章・本文・意図タグ・ステータス（`draft` / `approved` / `returned`）。
- `brief_log.json`: 承認・差戻し操作の履歴（HITL で編集した場合に追記）。
- `brief_ai_log.json`: 生成 AI の呼び出しログ。モデル名、プロンプトテンプレート、警告、トークン使用量を含む。
- `ai_generation_meta.json`: ポリシー ID、入力ハッシュ、カードごとの `content_hash`・`story_phase`・意図タグ・行数、統計値、選択した `mode`（`dynamic` / `static`）。
- `brief_story_outline.json`: 章 ID とカード ID の対応表。工程3 の章構成初期化に利用する。
- `audit_log.json`: 生成時刻、ポリシー ID、成果物パス、実行モード（将来的に SHA256 も記録予定）。

## 業務フロー
1. CLI がブリーフ入力を読み込み、`BriefSourceDocument` へパースする。Markdown の見出しや箇条書きはカード候補に変換される。
2. `BriefAIOrchestrator` がポリシー定義を評価し、カードを生成。生成枚数は `-p/--page-limit` が指定されていない限りポリシーまたは LLM 任せ。
3. 生成結果を Pydantic モデルで検証し、`prepare_card.json` と関連ログファイルを出力する。
4. 監査ログ (`audit_log.json`) に成果物パスと統計情報を記録する。将来的に SHA256 ハッシュを追加し改ざん検知を行う。
5. 工程3 `pptx compose` が `--brief-cards` / `--brief-log` / `--brief-meta` オプションで成果物を参照し、章構成とマッピングを実行する。

## 監査・品質要件
- 生成 AI が警告を返した場合は `brief_ai_log.json.warnings` に記録し、CLI 標準出力にも WARN を表示する。
- `ai_generation_meta.json.statistics.cards_total` と `prepare_card.json.cards.length` が一致すること。
- `ai_generation_meta.json.mode` と `audit_log.json.brief_normalization.mode` が一致し、後工程で参照できるように保持すること。
- 生成カードの `status` 初期値は `draft`。HITL 承認後に `approved` / `returned` を設定して `brief_log.json` へ記録する。
- 入力ブリーフのハッシュ (`input_hash`) は `audit_log.json` と `ai_generation_meta.json` の両方で整合させる。

## CLI 要件
- `pptx prepare <brief_path>` はブリーフが存在しない場合に exit code 2 を返す。
- `--mode` オプション（`dynamic` / `static`）を必須とし、実行モード未指定の場合は CLI がエラーで終了する。
- ポリシー読み込み失敗時（`BriefPolicyError`）は exit code 4 で終了し、エラーメッセージを標準エラーへ出力する。
- 生成結果は `.pptx/prepare/` 配下へ出力し、ディレクトリが存在しない場合は自動生成する。
- `-p/--page-limit` を指定した場合、生成枚数が制限値を超えた際に WARN を出力してリストをトリムする。
- `--output` を指定して別ディレクトリへ書き込む際もファイル構成（`prepare_card.json` 等）は変えない。

## 今後の拡張
- ブリーフ差分比較（再生成時の変更可視化）機能。
- 営業メモや CRM からの直接インポート（Markdown 自動生成）機能。
- 承認 UI と BriefCard 編集 API。差戻しフローとの統合は RM-051 で管理。
- 生成 AI のプロバイダーを CLI オプション化（現状は環境変数 `PPTX_LLM_PROVIDER` で切替）。
