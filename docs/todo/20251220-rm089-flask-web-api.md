目的: RM-089 stage1-4 Flask Web/API 化の着手と実装準備（API基盤設計・成果物返却フロー整理）
関連ブランチ: feat/rm089-flask-web-api
関連Issue: #446
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm089-flask-web-api を作成し、OpenAPI 調整や設計メモ追加を含む複数コミットを push 済み
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: Plan 承認済み（チャットで「ok」受領 2025-12-20）。  
    - 対象整理（スコープ、対象ファイル、前提）: RM-094 非同期基盤と RM-092 出力配置を前提に、Flask Web/API で stage1-4（templates/prepare/compose/gen）と jobs/transactions を提供。gen は成果物 URL を返却。  
    - ドキュメント／コード修正方針: OpenAPI 3.1 を `docs/design/api/openapi.yaml` に整備し契約先行。Flask app factory + Blueprint で API 層を新設し、ジョブ実行ラッパを API 化。成果物パスは `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` 規約に従う。README/requirements/design を実装後に更新予定。  
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo へ反映し、PR で OpenAPI と実装の差分をレビュー。必要に応じて API 契約テストを共有。  
    - 想定影響ファイル: Flask 入口/Blueprint、`src/pptx_generator/pipeline/base.py` 近辺（コンテキスト生成・workdir 解決）、ジョブ実行ラッパ、OpenAPI spec、設計/要件ドキュ。  
    - リスク: 署名付き URL/認証方針の未確定、CLI との成果物互換性、OpenAPI と実装のドリフト。  
    - テスト方針: API ハンドラ単体テストで job_id/transaction_id・成果物パスを検証。時間が許せば最小フローの smoke を追加。OpenAPI と実装のルート/必須フィールド整合チェックを組み込み。  
    - ロールバック方法: 変更を分割コミットし、問題発生時は該当コミットを revert。  
    - 承認メッセージ ID／リンク: チャット承認（2025-12-20 “ok”）
- [x] 設計・実装方針の確定
  - メモ: 認証/認可設計（HMAC+Bearer OR, 鍵ローテ, 署名計算, エラー方針）を `docs/design/api/auth.md` に整理。Flask API 構成・ミドルウェア・成果物取得・設定・テスト方針を `docs/design/api/flask.md` に整理。OpenAPI から両設計メモへリンク済み。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 進め方メモ
    1) 骨組み実装（Flask app factory + Blueprint ルートのみ、認証ミドルウェア実装、ジョブ登録はダミーで job_id/transaction_id/status=pending を返す）
    2) 薄いテスト追加（認証OK/NG、各ルートの 202/401/404 スモーク、artifacts 認証テスト）
    3) 実処理組み込み（RM-094 キュー呼び出し、workdir 解決、成果物返却）＋テスト拡張
- [ ] テスト・検証
  - メモ: 実施したテスト内容と結果を記入する
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
