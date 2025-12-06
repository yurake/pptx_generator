---
目的: RM-056 多形式インポート CLI 操作統合の実装と運用整備
関連ブランチ: feat/rm056-cli-integration
関連Issue: #364
roadmap_item: RM-056 多形式インポートCLI統合
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から `feat/rm056-cli-integration` を作成し、初回コミットは不要だったため未作成。remote へ push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: `pptx prepare` で複数 PREPARE_PATH を受け付け、ContentImportService を統合して PDF/URL/data URI を stage2 へ渡す。既存 prepare 入力互換を維持。
    - ドキュメント／コード修正方針: CLI 引数ハンドリングを更新し、インポート結果を PrepareSourceDocument へ変換するヘルパーを追加。ai_generation_meta / audit_log にソースメタを追記し、関連ドキュメント（CLI リファレンス・stage2要件・samples）を改訂。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo へ進捗記録、ユーザー承認済み Plan を基に作業。テスト結果は pytest コマンド記録。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `cli_commands/prepare.py`, `cli_handlers/prepare.py`, `prepare/models.py`, `tests/cli/test_cli_prepare_stage_flow.py`, 各種 docs/samples。
    - リスク: LibreOffice 未導入環境で PDF 変換が失敗する可能性、複数入力統合時の章順序が想定通りか要検証。
    - テスト方針: CLI テストを中心に `tests/cli/test_cli_prepare_stage_flow.py` を実行し、ContentImportService の既存単体テストで変換を確認。
    - ロールバック方法: CLI とハンドラ変更コミットを revert し、`docs/` の該当更新を同時に戻す。
    - 承認メッセージ ID／リンク: ユーザー「いいね、承認します。」(2025-12-03)
- [x] 設計・実装方針の確定
  - メモ: Plan どおり CLI で入力配列を正規化し、構造化ファイルは従来パーサ、その他は ContentImportService 経由で PrepareSourceDocument を構築する方針に確定。ai_generation_meta / audit_log へ import_sources を記録し、警告は CLI メッセージへ転記。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
    - メモ: 設計内容は本 ToDo と Plan へ記録済み。新規ノート追加は不要。
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: CLI/ハンドラ/モデルを更新し、複数 PREPARE_PATH の解析・インポート変換・meta 追記を実装。ContentImportService 統合用ヘルパー `_load_prepare_inputs` 等を追加。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py tests/content_import/test_content_import_pipeline.py` を実行し 16 件成功。
  - [x] UAT 実行（Case M1）
  - [x] UAT 実行（Case T1）
  - [x] UAT 実行（Case B1）
  - [x] UAT 実行（Case H1）
  - [x] UAT 実行（Case P1）
  - [x] UAT 実行（Case MX）
  - [x] UAT 実行（Case U1）
  - メモ: UAT 手動検証の記録テンプレートを以下へ追記。各ケース実行後に「実行結果」を更新すること。

    | ケースID | 入力種別 | 実行コマンド | 確認観点 | 実行結果メモ |
    |----------|----------|---------------|------------|---------------|
    | M1 | Markdown | `uv run --extra dev pptx prepare samples/input/pitch.md --mode dynamic --output .uat/pitch` | `import_sources[0].via == "structured"`、先頭カードは `title` があり `headline` が `null` | OK: structured, title-only card |
    | T1 | プレーンテキスト | `uv run --extra dev pptx prepare samples/input/blog.text --mode dynamic --output .uat/blog` | `via == "structured"`、本文ブロックが `paragraph` で生成される | OK: structured, body=paragraph |
    | B1 | 箇条書きMarkdown | `uv run --extra dev pptx prepare samples/input/bullet_only.md --mode dynamic --output .uat/bullet` | `via == "structured"`、`body[*].type == "bullets"` で階層が 3 未満 | OK: structured, bullet blocks detected (items空) |
    | H1 | HTMLファイル | `uv run --extra dev pptx prepare samples/input/landing_page.html --mode dynamic --output .uat/html` | `via == "content_import"`、HTML 変換で `warnings` が空 | OK: content_import, warnings=None |
    | P1 | PDF | `uv run --extra dev pptx prepare samples/input/landing_page.pdf --mode dynamic --output .uat/pdf` | `via == "content_import"`、TXT 生成成功・`warnings` 空・`audit_log` に fallback 記録 | OK: content_import, warnings=None (fallback不要) |
    | MX | 複数入力 | `uv run --extra dev pptx prepare samples/input/pitch.md samples/input/landing_page.pdf --mode dynamic --output .uat/mixed` | `import_sources` に2件（structured + content_import）、カード枚数が増加 | OK: sources=2 (structured+content_import), cards=2 |
    | U1 | URL | `uv run --extra dev pptx prepare https://github.com/yurake/pptx_generator/blob/main/README.en.md --mode dynamic --output .uat/url` | `via == "content_import"`、`content_type` が `text/html`、`warnings` 空 | OK: content_import, content_type=text/html, warnings=None |
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
    - メモ: ロードマップ記載内容に変更なしのため更新不要。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: stage-02 要件に複数 PREPARE_PATH と import_sources の記録仕様を追記。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: CLI コマンドリファレンスに多形式インポート手順と複数引数例を追加。
  - [x] docs/runbook 配下
    - メモ: 影響する運用手順なしのため更新不要。
  - [x] README.md / AGENTS.md
    - メモ: 本件は `samples/AGENTS.md` を更新。ルート README は影響なし。
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
  - メモ: 該当 Issue なしのため `未作成` を維持。
- [x] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [x] PR 作成
  - メモ: PR #374 https://github.com/yurake/pptx_generator/pull/374（2025-12-05 完了）

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
