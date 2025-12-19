目的: RM-089 stage1-4 Flask Web/API 化の着手と実装準備（API基盤設計・成果物返却フロー整理）
関連ブランチ: feat/rm089-flask-web-api
関連Issue: 未作成
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm089-flask-web-api を作成（初期コミット未作成・push 未実施）
    - 必ずmainからブランチを切る
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認待ち Plan（OpenAPI 整合込み）  
    - 対象整理（スコープ、対象ファイル、前提）: RM-094 の非同期基盤（キュー/ジョブ状態）と RM-092 の出力配置規約を前提に、Flask Web/API で stage1-4 を提供。エンドポイントは templates/prepare/compose/gen と jobs/transactions のステータス取得。gen は成果物 URL を返却。  
    - ドキュメント／コード修正方針: OpenAPI 3.1 仕様を `docs/api/openapi.yaml`（想定）に起こし契約先行で実装。Flask app factory + Blueprint を新設し、RM-094 の実行ラッパを API 化。成果物返却/パスは RM-092 の `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` に従う。README/requirements/design へ API 利用手順とスキーマを追記。  
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo へ反映し、PR で OpenAPI と実装の差分をレビュー。必要に応じて API 契約テストを共有。  
    - 想定影響ファイル: Flask 入口/Blueprint 新規追加箇所、`src/pptx_generator/pipeline/base.py` 近辺（コンテキスト生成・workdir 解決）、ジョブ実行ラッパ、OpenAPI spec (`docs/api/openapi.yaml` 想定)、設計/要件ドキュ。  
    - リスク: 署名付き URL/認証方針の未確定、CLI との成果物互換性、OpenAPI と実装のドリフト。  
    - テスト方針: API ハンドラ単体テストで job_id/transaction_id・成果物パスを検証。時間が許せば最小フローの smoke を追加。OpenAPI と実装のルート/必須フィールド整合チェックを組み込み。  
    - ロールバック方法: 変更を分割コミットし、問題発生時は該当コミットを revert。  
    - 承認メッセージ ID／リンク: 承認待ち
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
- [ ] テスト・検証
  - メモ: 実施したテスト内容と結果を記入する
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
