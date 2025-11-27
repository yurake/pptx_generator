# 2025-11-03 テンプレ stage 統合集約メモ

## 背景
- ロードマップ項目 **RM-051 テンプレ stage 統合集約** に基づき、旧 stage 1（テンプレ準備）と旧 stage 2（テンプレ構造抽出）を統合し、新しい「stage 1: テンプレ stage」として再定義した。
- CLI 利用者には `uv run pptx template` を標準ルートとして案内し、従来の `tpl-extract` / `layout-validate` / `tpl-release` は詳細オプションに位置付ける。
- 4 stage 体系（テンプレ stage → コンテンツ準備 → マッピング → レンダリング）へ移行するにあたり、主要ドキュメント・テスト・サンプルを更新した。

## 主な変更
- **CLI**: `src/pptx_generator/cli.py` に `template` サブコマンドを追加。抽出と検証を一括実行し、`--with-release` 指定時はリリース成果物も生成。既存 `tpl-extract` / `layout-validate` / `tpl-release` は共通ヘルパーを共有する形で維持。
- **テスト**: `tests/test_cli_integration.py` と `tests/test_cli_cheatsheet_flow.py` に `template` コマンドのケースを追加し、旧フローの期待値を更新。
- **ドキュメント**:
  - `README.md`、`docs/design/design.md`、`docs/design/cli-command-reference.md`、`docs/requirements/requirements.md` を 4 stage 構成へ改訂。
  - `docs/requirements/stages/` および `docs/design/stages/` のステージファイルを新番号へリネームし、旧 stage 2 ドキュメントは統合済みの旨を stub 化。
  - ロードマップ・ToDo 参照用に本メモを追加。
- **ToDo**: `docs/todo/20251103-rm-051-template-integration.md` に Plan を反映し、関連ブランチを更新。

## フォローアップ候補
- `docs/roadmap/roadmap.md` の内部リンク・stage 表記を最新の 4 stage へ更新（次ブランチで対応予定）。
- `docs/design/stages/stage-01-template-pipeline.md` の詳細化（抽出ワークフロー図、例外ハンドリングの整理）。
- CI でのテンプレ検証ジョブ（`tpl-extract` / `layout-validate`）自動実行の設計。

## 関連参照
- `docs/requirements/stages/stage-01-template-pipeline.md`
- `docs/design/cli-command-reference.md`
- `tests/test_cli_cheatsheet_flow.py`
