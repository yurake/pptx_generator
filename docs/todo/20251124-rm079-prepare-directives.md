---
目的: RM-079 pptx prepare directive 拡張
関連ブランチ: 未作成
関連Issue: #318
roadmap_item: RM-079 pptx prepare directive 拡張
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm079-directives (ローカル作成、push これから)
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/cli.py` の `prepare` サブコマンド、`pptx_generator/prepare/orchestrator.py`、`prepare/prompts.py`、`prepare/models.py`、`pptx_generator/prepare/llm_client.py` を対象に directive 取扱いを拡張。生成メタ・AI ログへの記録が前提。
    - ドキュメント／コード修正方針: CLI オプションとして `--prompt-directive` / `--prompt-directive-file` を追加し、複数指定とファイル読み込みをサポート。プロンプト生成 payload に directives 配列を渡し、メタ情報へ格納する。README・CLI リファレンス・サンプル JSON を更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: `docs/design/cli/cli-command-reference.md` と README の該当節を更新し、ToDo へテスト結果とディレクティブ仕様を記録。PR では新オプションの使用例とセキュリティ留意点を説明する。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/prepare/orchestrator.py`, `src/pptx_generator/prepare/prompts.py`, `src/pptx_generator/prepare/models.py`, `src/pptx_generator/prepare/llm_client.py`, `tests/test_cli_prepare.py`, `tests/test_cli_integration.py`, `docs/design/cli/cli-command-reference.md`, `README.md`.
    - リスク: 外部文字列の組み込みで JSON フォーマットが破損するリスク。directive 内容が LLM 応答に影響し、想定外の出力になる可能性。入力検証とログ出力で状況把握を行う。
    - テスト方針: `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_cli_integration.py::test_cli_prepare_generates_outputs` を実行し、directive 指定あり／なし両方を検証。必要ならモッククライアントのテストを追加。
    - ロールバック方法: CLI オプション追加コミットと orchestrator の変更を revert し、docs の追加記述も巻き戻す。
    - 承認メッセージ ID／リンク: ユーザー承認「ok」（2025-11-24 の会話メッセージ）を参照。
- [ ] 設計・実装方針の確定
  - メモ: 
- [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
- [ ] ドキュメント更新（要件・設計）
  - メモ: 確定した設計・実装方針を要件／設計ドキュメントへ反映し、変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 
- [ ] テスト・検証
  - メモ: 
- [ ] ドキュメント更新
  - メモ: 
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
