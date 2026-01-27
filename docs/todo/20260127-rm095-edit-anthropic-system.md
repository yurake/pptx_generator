---
目的: RM-095 Stage5 PPTX 編集反映 / Anthropic system パラメータ修正
関連ブランチ: feat/rm095-edit-anthropic-system
関連Issue: #565
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-27: feat/rm095-edit-anthropic-system を作成。初期コミット=b85ef2f（ToDo追加）。push済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: Anthropic Edit クライアントの system パラメータをトップレベルに移動。対象は src/pptx_generator/edit_ai/client.py と tests/edit_ai/test_client_providers.py。
    - ドキュメント／コード修正方針: messages から system を除外し、messages.create の top-level 引数 `system` に EDIT_SYSTEM_PROMPT を渡す。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo に進捗/結果を記録し PR 本文へテスト/UAT結果を記載。
    - 想定影響ファイル: edit_ai/client.py、tests/edit_ai/test_client_providers.py。
    - リスク: Anthropic SDK の引数互換性、既存 mock テストの引数期待が変わる。
    - テスト方針: `uv run --extra dev pytest tests/edit_ai/test_client_providers.py -k anthropic`、`uv tool run diff-cover coverage.xml --compare-branch upstream/main`。
    - ロールバック方法: Anthropic の system 引数変更とテスト修正を revert。
    - 承認メッセージ ID／リンク: 2026-01-27 ユーザー承認「OK」
- [x] 設計・実装方針の確定
  - メモ: AnthropicEditClient.rewrite で messages から system を除外し、system は top-level 引数へ移動。
  - [x] 設計・実装方針メモの共有（不要）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: messages.create の top-level に system を追加し、_build_claude_messages から system を除外。Anthropic 専用テストを追加。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト:
      - `uv run --extra dev pytest tests/edit_ai/test_client_providers.py -k "anthropic"`
        - 結果: 2 passed
      - `uv tool run diff-cover coverage.xml --compare-branch upstream/main`
        - 結果: No lines with coverage information in this diff.
    - ユーザー経路の手動確認（必要な場合）: 変更は SDK 呼び出し引数のため不要
    - 生成物の確認があれば、その方法と結果: なし
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（変更不要: 既存 RM-095 の運用更新なし）
  - [x] docs/requirements 配下（変更不要: 仕様変更なし）
  - [x] docs/design 配下（変更不要: 設計変更なし）
  - [x] docs/runbook 配下（変更不要: 運用手順変更なし）
  - [x] README.md / AGENTS.md（変更不要: 手順追加なし）
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` を #565 に更新。
- [x] チェックリスト整合確認
  - メモ: 実装/テスト/ドキュメントまで完了。残りは PR 作成。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: Anthropic の system は top-level に配置する。
  - 決定と理由: Anthropic SDK の仕様準拠。
  - リスク(UNCONFIRMED): SDK バージョン差異で挙動が変わる可能性。
  - Now/Next: 実装・テスト完了。次は Issue/PR 作成。
  - テスト実績/抜け: pytest 2件パス、diff-cover は対象行なし。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
