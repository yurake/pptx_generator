# 工程1 テンプレ工程 要件詳細

## 概要
- ブランドガイドに沿ってテンプレート資産を設計・改修し、版管理と承認フローを標準化する。
- 承認済みテンプレートから構造情報（`template_spec.json` / `jobspec.json`）とブランド設定を抽出し、後続工程がテンプレ依存の座標やアンカーを参照できる状態にする。
- 抽出結果の妥当性を自動検証し、差分レポートや診断情報を用いて品質を担保する。
- リリースメタ (`template_release.json`) を生成し、ゴールデンサンプル検証と環境メタを含む監査ログを整備する。

## 入力
- ブランドガイドライン、レイアウトカテゴリ定義、命名規約 (`PH__` 前提)。
- 改訂対象のテンプレート PPTX（`/templates/libraries/<brand>/<version>/template.pptx` 想定）。
- 既存テンプレートの `template_release.json` / `layouts.jsonl`（差分比較に利用）。
- Analyzer が出力した `analysis_snapshot.json`（任意。アンカー突合検証に利用）。

## 成果物
- 承認済みテンプレート PPTX（最新版）。
- `.pptx/extract/<template_id>/` 内の成果物
  - `template_spec.json`（または `template_spec.yaml`）
  - `jobspec.json`
  - `branding.json`
  - `layouts.jsonl` / `diagnostics.json` / `diff_report.json`（比較時のみ）
- `.pptx/release/` 内の成果物（`--with-release` 指定時）
  - `template_release.json`
  - `release_report.json`
  - `golden_runs.json` および `golden_runs/<spec名>/`（ゴールデンサンプル実行時）

## ワークフロー
1. **テンプレ設計・準備（HITL）**
   - レイアウト構成、フォント・配色、図形配置を策定し、ブランド側の承認を得る。
   - 重複／欠落プレースホルダが無いか、命名規約に沿っているかをチェックする。
   - テンプレ修正の目視検証を行い、重大な崩れがないことを確認する。
2. **構造抽出と検証（自動）**
   - `uv run pptx template <template.pptx>` を実行し、テンプレ仕様・ジョブスペック雛形・ブランド設定を抽出する。
   - 同コマンドによりレイアウト検証 (`layouts.jsonl` / `diagnostics.json`) を実行し、欠落プレースホルダや未知アンカーがないか確認する。
   - Analyzer スナップショットが提供された場合は差異を `diff_report.json` に記録し、レビュー対象とする。
3. **リリースメタ生成（必要に応じて）**
   - リリースメタが必要な場合は `uv run pptx template <template.pptx> --with-release --brand <brand> --version <ver>` を実行し、`template_release.json` を生成する。
   - ゴールデンサンプル検証を行う場合は `--golden-spec` を指定し、互換性エラーを `template_release.json` の diagnostics に反映する。
4. **成果物アーカイブと配布**
   - 抽出成果物とリリースメタをリポジトリ／テンプレ資産管理ストレージへ配置し、後続工程（コンテンツ正規化・マッピング）から参照可能にする。

## 推奨 CLI
- 標準フロー: `uv run pptx template templates/libraries/acme/v1/template.pptx --output .pptx/extract/acme_v1`
- リリースメタ生成を含める場合: `uv run pptx template templates/libraries/acme/v1/template.pptx --with-release --brand ACME --version v1 --output .pptx/extract/acme_v1`
- 高度な運用（個別コマンドの活用）は `docs/design/cli-command-reference.md` の「テンプレ工程詳細オプション」を参照する（`tpl-extract` / `layout-validate` / `tpl-release` を直接呼び出すケース）。

## 品質ゲート
- プレースホルダ構成
  - レイアウトごとに必須プレースホルダ（title, body, note 等）が揃っていること。
  - プレースホルダ名に重複がないこと。`layouts.jsonl` で `duplicate_anchor_names` が検出された場合は差戻し。
- 抽出・検証結果
  - `diagnostics.json.errors` が空であること。警告 (`warnings`) が存在する場合はレビューで対応方針を決定する。
  - `template_spec` / `jobspec` のスキーマ検証に通過し、アンカー命名と用途タグが定義されていること。
- リリースメタ
  - `template_release.json.diagnostics.errors` が空であること。ゴールデンサンプル失敗や抽出エラーは差戻し対象。
  - `release_report.json` の `changes` に想定外の差分がないこと。

## 監査・運用
- `template_release.json.summary` にレイアウト数・アンカー数・警告件数を収集し、過去バージョンと比較する。
- `release_report.json` でハッシュ値と差分レポートを管理し、改訂理由を追跡する。
- 抽出時に生成される `diagnostics.json` の処理時間・警告件数を記録し、再発時は `docs/notes/` にフォローアップを追加する。
- ゴールデンサンプル実行ログ (`golden_runs/`) は互換性検証の証跡として保管し、失敗時は Issue にリンクする。

## 未実装項目（機能単位）
- テンプレ版比較レポートの自動通知ジョブおよび配布チャネル統合。
- 抽出結果の可視化 UI（レイアウト差分ヒートマップ、警告 dashboard）。
- `tpl-extract` / `layout-validate` の CI 統合パイプライン（複数テンプレの一括検証）。
- ゴールデンサンプル自動生成と回帰失敗時の自動 Issue 起票。
