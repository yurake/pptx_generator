---
目的: RM-086 静的テンプレ外部フック統合の準備
関連ブランチ: docs/rm086-static-hooks-prep
関連Issue: #368
roadmap_item: RM-086 静的テンプレ外部フック統合
---

- [x] ブランチ作成・初期コミット・push
  - メモ: docs/rm086-static-hooks-prep を main から切り、初期コミットを push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: CLI 静的モード時に外部フックを stage ごと・スライドごとに解決する仕組みを追加し、テンプレ ID（PPTX ファイル名由来）ごとの `external/<template_id>/hooks.json` を解釈できるようにする。Stage 1〜4 の既存コマンドにフック実行ポイントを挿入し、未定義時は従来処理を維持する。スライド単位のフック指定は `スライド番号_レイアウト名` 規則で扱う。
    - ドキュメント／コード修正方針: `src/pptx_generator/cli.py` および各ステージコマンド生成関数へフック実行ロジックを追加し、新しいヘルパーモジュールで設定読み込み・実行を実装。外部設定スキーマと運用手順を `docs/design` / `docs/policies` に反映し、ToDo にも整合を記載。
    - 確認・共有方法（レビュー、ToDo 更新など）: 実装差分は PR でレビュー。ToDo を随時更新し、重要決定は `docs/notes/20251204-rm086-static-hooks.md` に追記。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/cli_commands/*`, 新規 `cli_hooks` モジュール群, `docs/design`, `docs/policies`, テストコード（`tests/cli`, `tests/integration` など）。
    - リスク: 外部フック失敗時の CLI 停止に備えたエラーハンドリング、`external/` 不在時のフォールバック、スライド別設定の複雑化、テスト環境での `external` モック管理。
    - テスト方針: ユニットテストで設定パースと優先順位、結合テストでダミーフックを呼び出す CLI フロー、エラーパス検証、`uv run --extra dev pytest` による回帰確認。
    - ロールバック方法: 実装コミットを `git revert` で戻し、追加ドキュメントも同ブランチで削除。外部設定を利用しないことで旧フローへ戻せる。
    - 承認メッセージ ID／リンク: （本チャットでの承認）
- [x] 設計・実装方針の確定
  - メモ: CLI 全ステージ（template/prepare/compose/mapping/gen）で静的モード時に `external/<template_id>/hooks.json` を解釈し、ステージ前後のフックとスライド別フックを呼び出す設計に決定。テンプレート ID は PPTX ファイル名 stem から導出し、スライドキーは `.pptx/extract/prompts/01_system-layout.md` と同じ `NN_slug` 形式で揃える。ENV 変数一覧（PPTX_STAGE など）を整理し、ステージ後に生成物パスを追加で渡す。TODO: ドキュメントへ使用方法を追記。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
    - メモ: 詳細は `docs/notes/20251204-rm086-static-hooks.md` に会話ログとして記録済み。今後の追記は同ファイルへ集約する。
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `src/pptx_generator/cli_hooks/*` を新設し、`cli_commands` 各ステージにフック制御を組み込み済み（コミット: `feat(cli): add external hook support for static mode`, `feat(cli): invoke slide-level hooks after stages`）。外部フック前に `pyproject.toml` / `uv.lock` を検知して `uv sync` を自動実行し、`ModuleNotFoundError` 等が出た場合は 1 度だけ再同期→再実行するリトライを追加。ドキュメント反映は未実施。次は `temp/excel_mapper.py` をステージごとのフックスクリプトへ分割し、`external/jri_template/` で管理する方針に変更。
  - メモ追記 (2025-12-06): Stage4 フックで `templates/経費投資.pptx` のレイアウトを複製し、静的文言（x．提示金額、＜ご参考...＞ 等）を保持したままメッセージラインと表セルを埋め込む処理を実装。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/cli/test_cli_hooks.py` を実行し、外部フック設定・スライドキー生成・template_id ヘルパーに加え、`uv sync` 自動実行とリトライ制御（失敗時のフォールバックなし）を検証するユニットテストを通過。カバレッジ XML を再生成済み。
- [x] 外部フック運用検証
  - メモ: `external/jri_template/` に Stage ごとの実スクリプトを配置し、`hooks.json` から呼び出す構成で静的テンプレ用パイプラインを再現する。`temp/excel_mapper.py` を Stage1〜4 相当の Python スクリプトへ分割し、CLI 実行時に外部フックだけで Excel → prepare_card.json → generate_ready.json → 静的 PPTX 生成まで流せることを確認する。
  - [x] 実装
    - メモ: 
      1. フック配置をテンプレ ID (`external/経費投資テンプレ/`) に合わせて整理し、`hooks.json` を `template/prepare/mapping/gen` へ割り当てる構成に統一。  
      2. Stage1 でコンテキスト (`runtime/context.json`) を保存し、Stage2/3 では Excel 抽出結果に `meta.template_id` を付与して `generate_ready.json` まで引き継げるよう `stage02_prepare.py` / `stage03_mapping.py` を調整（CLI のフック検知に必要）。  
      3. 以降は `uv run python stage0x_*.py` をフックから呼び出し、既存パイプライン成果物に影響しないよう `.pptx/jri/*` 配下で入出力を分離。
  - [x] テスト・検証
    - メモ: 静的モード向け CLI を以下の順で実行し、各ステージで外部フックが発火することを確認。  
      ```
      uv run pptx template temp/経費投資テンプレ.pptx --layout-mode static --template-id jri_template --output .pptx/jri/extract --force
      uv run pptx prepare --mode static --jobspec .pptx/jri/extract/jobspec.json --output .pptx/jri/prepare
      uv run pptx mapping .pptx/jri/extract/jobspec.json --prepare-cards .pptx/jri/prepare/prepare_card.json --output .pptx/jri/mapping --draft-output .pptx/jri/draft
      uv run pptx gen .pptx/jri/mapping/generate_ready.json --output .pptx/jri/gen --pptx-name jri_static_output.pptx
      ```
      生成物は `.pptx/jri/prepare/prepare_card.json`（`meta.template_id=経費投資` 付き）、`.pptx/jri/mapping/generate_ready.json`、`.pptx/jri/gen/jri_static_output.pptx`。テンプレ指定が `templates/経費投資.pptx` の場合でも、サンプルスライドが空のときは既存テンプレ（`external/経費投資/assets/経費投資テンプレ.pptx`）へ自動フォールバックするよう Stage2/Stage4 フックでテンプレ解決・フォント適用を行い、Stage1 フックは撤去して prepare フック単体で前提情報を解決する構成へ整理した。
      `.pptx/jri/gen/jri_static_output.pptx` の表セル値と `external/経費投資/runtime/context.json` の `extract_summary.table` を `uv run python` スニペットで突合し、値が一致することも確認済み。
- [x] ドキュメント更新
  - メモ: RM-086 の進捗・テーブルマッピング手順を `docs/roadmap/roadmap.md`, `docs/requirements/requirements.md`, `docs/runbooks/release.md`, `docs/runbooks/runbooks.md`, `README.md`, `AGENTS.md` に反映済み。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
    - メモ: ガント図を「進行中」に更新し、期待成果へ Excel マッピング達成済みを追記。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: 静的テンプレ向け `mapping_config.json` と表セル突合要件を追加。
  - [x] docs/runbook 配下
    - メモ: `release.md` に表突合テストの Python スニペットを追加し、索引も同期。
  - [x] README.md / AGENTS.md
    - メモ: 静的テンプレの `mapping_config.json` と検証手順を紹介する注記を追加。
  - [x] scripts/ 配下
    - メモ: `inspect_static_pptx.py` を追加し、テンプレートと生成結果の差分を CLI で確認可能にした。
- [ ] external/ 配下 README・AGENTS 整備
  - メモ: `external/<template_id>/` に README.md / AGENTS.md を追加し、外部フック運用手順と静的テンプレ仕様を記載する。
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: ドキュメント更新と検証タスクをすべて完了したことを再確認済み。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
