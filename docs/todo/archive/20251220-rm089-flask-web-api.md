---
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
- [x] 実装
  - メモ: Flask app factory + Blueprint で stage1-4/templates/prepare/compose/gen/jobs/transactions/artifacts を実装、認証（Bearer/HMAC）と body サイズ制限・JSONバリデーションを追加。キュー実行に InProcessJobQueue を利用し、成果物ダウンロード `/jobs/{job_id}/artifacts/{pptx|pdf}` をサポート。FastAPI は前提通り未使用。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/api/test_flask_app.py`（22件）を実行し全件成功。認証OK/NG、署名スキュー、JSON必須、job flow、artifacts有無、エラー -> 422/404/401 マッピング、prepare→compose→gen スモーク、テンプレート実行で成果物生成までカバー。
- [x] ドキュメント更新
  - メモ: Flask への統一に伴い、FastAPI 言及を除去・整合。現時点で README/AGENTS/runbook/roadmap/requirements は追加変更不要と判断し、理由を明記する。
  - [x] docs/roadmap 配下（フレームワークを Flask 前提に確認。追加変更なし。）
  - [x] docs/requirements 配下（API 仕様整合を再確認。追加変更なし。）
  - [x] docs/design 配下（Flask 設計メモを最新化済み。OpenAPI を tx レジストリ方式へ更新済み。） 
  - [x] docs/runbook 配下（追加変更不要を確認。）
  - [x] README.md / AGENTS.md（FastAPI 依存がないことを確認。追加変更不要。）
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: ドキュメント更新以外の親子タスクを再確認し整合完了。
- [x] PR 作成
  - メモ: PR #456 https://github.com/yurake/pptx_generator/pull/456（2025-12-25 完了）

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
