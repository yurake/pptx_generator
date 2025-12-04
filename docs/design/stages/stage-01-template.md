# stage 1 テンプレ準備 設計

## 目的とスコープ
- ブランドごとのテンプレ資産を安定して提供し、後続 stage が追加メタ無しで利用できる状態を作る。
- テンプレ構築は PowerPoint 操作（人手）が主体だが、品質担保と受け渡しは自動化を前提に設計する。

## アーキテクチャ構成
| モジュール | 役割 | 主な技術 / ツール |
| --- | --- | --- |
| Template Authoring | PPTX 編集・レイアウト設計 | PowerPoint, Figma（参考） |
| Template Release CLI | `template_release.json` 生成、差分チェック起動 | Python, `python-pptx`, Click |
| Golden Sample Runner | 代表 spec / レンダリングジョブの実行 | `uv run pptx gen`, LibreOffice |

### Template AI 連携
- `layout_validation` ステップで Template AI サービスを初期化し、レイアウトごとのプレースホルダー構造・テキスト／メディア推定・ヒューリスティックタグを payload にまとめて LLM へ送る。
- プロバイダは `PPTX_TEMPLATE_LLM_PROVIDER`（未設定時は `PPTX_LLM_PROVIDER`）の環境変数を優先して解決し、OpenAI / Azure OpenAI / Anthropic Claude / AWS Bedrock（Claude）など Stage2/Stage3 と同じ LLM を選択できる。必要な環境変数（例: `OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `ANTHROPIC_API_KEY`, `AWS_REGION` など）は README や policy ドキュメントで案内し、適切に設定する。
- プロンプトやモデルの既定値は `config/template_ai_policies.json` で管理し、policy 単位で `provider` / `model` / `temperature` / `max_tokens` を上書きできる。
- `config/usage_tags.json` に canonical タグと説明、静的ルールを集約し、LLM 応答の正規化や `mock` 利用時のフォールバックに再利用する。
- `pptx_generator.template_ai.llm` ロガーへ JSON 応答を出力し、`diagnostics.json.template_ai` に推論ソース・タグ・未知語・エラーを記録する。静的ルールが適用された場合も同様に記録し、後続 stage から差分を確認できるようにする。
- 静的テンプレ専用フック: `.pptx/extract/` への成果物出力完了後、CLI はテンプレ ID（PPTX ファイル名 stem）に対応する `external/<template_id>/hooks.json` を探索する。静的モード (`--layout-mode static`) でフックが定義されていれば、ステージ完了後に以下を環境変数で提供して外部スクリプトを呼び出す。  
  - `PPTX_STAGE=template` / `PPTX_TEMPLATE_ID=<template_id>`  
  - `PPTX_TEMPLATE_SPEC_PATH` / `PPTX_JOBSPEC_SCAFFOLD_PATH` / `PPTX_BRANDING_PATH`  
  - スライド単位: `PPTX_SLIDE_KEY=NN_slug`（例: `01_system-layout`）、`PPTX_SLIDE_ID`、`PPTX_SLIDE_LAYOUT`、必要に応じて `PPTX_PROMPT_TEMPLATE_PATH`  
- フック設定が存在しない場合、静的モードの `pptx template` 実行時にスケルトン `external/<template_id>/hooks.json` を生成し、`stage` と `slides`（Blueprint 由来のキー）を `null` で初期化する。作成済みのファイルは上書きしない。
- フック設定ファイル例:
```json
{
  "stage": {
    "template": {
      "command": "./run_stage1.sh",
      "env": {
        "HOOK_OUTPUT": "./stage1.log"
      },
      "continue_default": false
    }
  },
  "slides": {
    "01_system-layout": {
      "template": {
        "command": "./hooks/01_system-layout.sh",
        "env": {
          "HOOK_OUTPUT": "./slides/01.log"
        }
      }
    }
  }
}
```
- スライドキー命名規則は `.pptx/extract/prompts/01_system-layout.md` と同一（2 桁ページ番号+スラグ化したレイアウト名）。フック実行結果に応じて `.pptx/` 配下へ追加成果物を配置し、既存のテンプレ抽出成果との整合を維持する。

## フロー詳細
1. **テンプレ編集**  
   - 作業結果を `templates/libraries/<brand>/<version>/template.pptx` に保存。  
   - PH 命名規約（`PH__<Role>__<Index>`）とレイアウト命名規約を遵守。
2. **自動診断 (仮)**  
   - Template Release CLI がテンプレを解析し、`template_release.json` と差分レポートを生成。  
   - ゴールデンサンプル指定時は `golden_runs.json` と `golden_runs/<spec_stem>/` 以下に検証ログを出力。  
   - 重複 PH / 不正レイアウト、ゴールデンサンプル失敗があれば診断エラーとして FAIL。
   - Analyzer 出力から issue/fix の件数をテンプレ受け渡しメタへ収集し、`analyzer_metrics` として集計する。差分レポートには baseline との差分が `analyzer.delta` として記録される。
   - `summary` セクションにレイアウト数・アンカー数・警告/エラー件数・Analyzer issue/fix 件数を集計し、`summary_delta` で品質推移を数値化する。
   - `environment` に Python / OS / CLI / LibreOffice / .NET SDK のバージョンを記録し、取得できなかった項目は診断警告に出力する。
3. **互換性チェック**  
   - Golden Sample Runner が既知 spec を用いてレンダリング → Analyzer → LibreOffice まで通し、互換性指標を算出。  
   - エラー時は差分レポートにハッシュとログパスを記録。
4. **アーカイブ**  
   - Release CLI が成果物（PPTX, release.json, diagnostics）を `templates/releases/<brand>/<version>/` にまとめる。

## インターフェース
- CLI: `uv run pptx tpl-release --template templates/.../template.pptx --brand <brand> --version <version> [--baseline-release <path>] [--golden-spec <spec.json>...]`
- 成果物: `template_release.json`, `release_report.json`, `golden_runs.json`, `golden_runs/<spec_stem>/`
- CI Hook (予定): PR 時に CLI を実行し、失敗時はレビューをブロック。

### 抽出・検証 CLI 補助
- `uv run pptx tpl-extract`: テンプレ PPTX から `template_spec.json`・`layouts.jsonl`・`jobspec.json` を抽出し、後続 stage が参照するメタデータを更新する。
- `uv run pptx layout-validate --template <path>`: レイアウトごとのプレースホルダー構造や禁則チェックを実行し、`diagnostics.json` と差分レポートを生成する。Golden Sample や Analyzer と組み合わせて品質ゲートを設計する。

## 監視・ログ
- Release CLI: 生成時刻、操作者、テンプレパス、検出エラーを構造化ログに記録。
- Golden Sample: 成功/失敗、LibreOffice exit code、差分件数。

## テスト方針
- CLI 単体テスト: release JSON スキーマ、差分出力、失敗時の exit code。
- 統合テスト: サンプルテンプレを用いた end-to-end リリース（PPTX → release → sample render）。

## 未解決事項 / TODO
- テンプレ差分検出アルゴリズム（図形比較 VS JSON 差分）の詳細設計。
- ゴールデンサンプルの自動生成と削除ポリシー。
- LibreOffice / Open XML Polisher のバージョン固定戦略。

## 関連スキーマ
- [docs/design/schema/stage-01-template-preparation.md](../schema/stage-01-template-preparation.md)
- サンプル: `docs/design/schema/samples/template_release.jsonc`, `docs/design/schema/samples/template_release_report.jsonc`
