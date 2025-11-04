# samples ディレクトリ向け作業指針

## 構成
- `json/sample_jobspec.json`: フル構成サンプル。アンカー付きテンプレートやリッチコンテンツの実装例を含む。
- `extract/`: 工程1 `pptx template` の出力サンプル。`template_spec.json` / `jobspec.json` / `branding.json` / `diagnostics.json` / `layouts.jsonl` を保持し、コマンド実行結果と同じファイル名を維持する。
- `prepare/`: 工程2 `pptx prepare` の成果物（`prepare_card.json`, `brief_log.json`, `ai_generation_meta.json`, `audit_log.json`, `brief_story_outline.json`）。CLI やテストで参照するため最新スキーマへ追従させる。
- `draft/`: 工程3 アウトライン承認の出力 (`draft_draft.json`, `draft_approved.json`, `draft_review_log.json`, `draft_meta.json`) を格納する。
- `compose/`: 工程3 マッピング結果 (`generate_ready.json`, `mapping_log.json`) を保存する。工程4 の成果物は `gen/` へ移動する。
- `gen/`: 工程4 `pptx gen` の成果物（`proposal.pptx`, `analysis.json`, `analysis_pre_polisher.json`, `review_engine_analyzer.json`, `rendering_log.json`, `monitoring_report.json`, `audit_log.json`）を格納し、PDF サンプルが生成できた場合は同ディレクトリへ追加する。
- `json/archive/`: 旧 `content_approved.json` 系サンプルを保管する領域。互換テストが不要になった場合は削除を検討する。
- `json/sample_template_layouts.jsonl`: 工程2のレイアウト候補を模した JSON Lines。ドラフト構成 CLI を手動確認する際の既定入力として使用する。
- `text/sample_import_content.txt`: 外部ソース取り込み向けのプレーンテキスト例。`pptx prepare --content-source` で工程2インポートを検証する際に利用する。
- `assets/`: テストやドキュメントで利用する画像・グラフなどの補助ファイルを配置（例: `logo.png`, `team.png`）。
- `templates/templates.pptx`: フル構成サンプルで利用する参照テンプレート。レイアウト名・アンカー図形の命名例を確認できる。`Timeline Detail` / `Comparison Two Axis` / `Fact Sheet` など RM-038 で追加したレイアウトに加え、RM-043 で拡充予定のバリエーションもここへ集約する。
- `skeleton.pptx`: 提案書の初期テンプレート。変更時は `docs/policies/config-and-templates.md` の手順に従い検証する。

## 運用ルール
- サンプル JSON は公開前提のダミーデータのみを使用し、実案件情報を含めない。
- `json/` 配下の `sample_jobspec*.json` を更新した際は `tests/test_cli_integration.py` の期待値や `docs/` の使い方ガイドを確認する。
- `prepare/` 配下のサンプルを更新する場合は、カード数・ストーリーフェーズ・intent タグの整合を確認し、必要に応じて CLI の生成手順を README へ反映する。
- `sample_template_layouts.jsonl` は 1 行 1 レコードの JSON Lines 形式を維持し、`layout_id`・`usage_tags`・`text_hint`・`media_hint` の最小セットを含める。用途が増えた場合はコメントをメモ欄へ追記する。
- テンプレートを差し替える場合は `uv run pptx gen` で出力差分を確認し、`docs/runbooks/release.md` に影響がないか検討する。
- 参照テンプレートにアンカーを追加する際は、レイアウト名と図形名が JSON 仕様と一致しているか確認する。

## テスト連携
- CLI 統合テストで参照されるため、フル構成サンプルのパスやスライド数の変更は `tests/test_cli_integration.py` のアサーションと合わせて更新する。
- `assets/` にファイルを追加した場合は、テストやドキュメントから相対パスで参照できるかを確認する。
- 最小構成サンプルはテスト対象に含めないが、CLI 動作確認手順に沿って生成ログを残す。

## レビュー時の確認ポイント
- サンプルが最新スキーマに準拠し、未使用フィールドや古いキーが残っていないか。
- テンプレート更新に伴い、ブランドカラーやフォントの整合性が取れているか（必要なら `config/branding.json` と併せて変更）。
- ドキュメントや README のサンプルコマンドが最新のファイル構成を反映しているか。
