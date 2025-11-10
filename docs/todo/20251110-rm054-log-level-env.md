---
目的: LOG_LEVEL 環境変数で CLI 全体のログレベルを制御できるようにする
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: #272
roadmap_item: RM-054 静的テンプレ構成統合
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm054-static-blueprint-plan` を継続利用（追加コミットで対応）
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記（2025-11-10 "おk"）
    - 対象整理（スコープ、対象ファイル、前提）: CLI 初期化コード（`src/pptx_generator/cli.py` ほかログ設定に関わる共通コード）で環境変数 `LOG_LEVEL` を参照し、Python 標準 logging のベースレベルを `debug`/`info`/`warning`/`error` 等へ統一的に設定する。従来の `OPENAI_LOG` は廃止し、新しい環境変数へ集約する。
    - ドキュメント／コード修正方針: CLI 起動時に `LOG_LEVEL` を読み込み、無効値は警告の上で既定レベルへフォールバック。OpenAI SDK も同じレベルを使うよう `openai` ロガーへ適用し、`OPENAI_LOG` を読んでいたコードがあれば削除。CLI ドキュメントへ新環境変数の説明を追記。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo を更新しつつ、ユーザーへ結果報告。必要に応じて関連メモへ記録。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, 既存設定ファイルやヘルパー（必要に応じて `src/pptx_generator/settings.py` など）、`docs/design/cli-command-reference.md`。
    - リスク: logging を初期化する順番により既存ハンドラのレベルが意図せず変わる可能性。`force` パラメータ使用時の副作用。OpenAI SDK のデフォルト挙動との齟齬。
    - テスト方針: `uv run --extra dev pytest tests/test_cli_integration.py -k log`（適切なケースが無ければスモールテスト追加）。手動で `LOG_LEVEL` を変えた CLI 実行を行い、ログ出力が想定通りか確認。
    - ロールバック方法: 追加したロガー設定とドキュメントの変更を `git revert` で戻す。`OPENAI_LOG` サポート復活も同様手順で可能。
    - 承認メッセージ ID／リンク: ユーザー承認 (2025-11-10, メッセージ "おk")
- [x] 設計・実装方針の確定
  - メモ: LOG_LEVEL を基点とした統一ログ制御と OPENAI_LOG 廃止方針を CLI へ反映する設計で合意
- [x] ドキュメント更新（要件・設計）
  - メモ: CLI 設計ガイドへ LOG_LEVEL の利用方法と OPENAI_LOG 廃止を追記
  - [ ] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `_determine_log_level` で環境変数と CLI フラグを統合解釈し、OpenAI ロガーにもレベルを適用
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_logging.py` を実行し、新規テスト3件が成功
- [ ] ドキュメント更新
  - メモ: 追加の README/Runbook 反映は未実施
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
