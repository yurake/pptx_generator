---
目的: RM-089 API の成果物パス自動解決（transaction_id 起点、パス指定廃止）
関連ブランチ: feat/rm089-flask-web-api
関連Issue: #449
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm089-flask-web-api で継続対応（新規ブランチ不要）
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan どおりにレジストリ方式を導入済み。
    - 対象整理: Flask API のパス指定廃止、transaction_id ベースで成果物を解決。
    - 修正方針: `PPTX_OUTPUT_ROOT/<tx>/registry.json` に最新ジョブと標準成果物パスを記録し、次ステージで参照。
    - 確認方法: API 単体テストで tx のみ指定パス無しを検証。
    - 想定影響: API I/F 破壊的変更、CLI/クライアント追従。実装済み。
    - リスク: レジストリ破損、tx 内多重ジョブの扱い。完了時に最新成功ジョブを記録。
    - テスト方針: prepare/compose/gen 正常系と 404/422 異常系を追加。
    - ロールバック: レジストリ導入コミットを分離済みで revert 可能。
- [x] 設計・実装方針の確定
  - メモ: 404(tx不明) / 422(前段成果物なし) ポリシーで確定。notes なし（ToDo に記載）。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: レジストリ導入、tx→前段成果物ルックアップ、パス指定廃止、OpenAPI 整合を実装済み。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/api/test_flask_app.py` で tx のみ指定ケースと 404/422 異常系をカバー済み。
- [x] ドキュメント更新
  - メモ: OpenAPI を tx レジストリ方式へ更新済み。追加の設計メモ不要と判断。既存 roadmap/requirements/design/runbook/README/AGENTS は整合確認済みで変更不要。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: PR 作成以外完了を確認。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
