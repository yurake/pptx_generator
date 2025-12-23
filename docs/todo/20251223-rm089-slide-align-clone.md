---
目的: RM-089 SlideIdAligner でレイアウト再利用を許可し、カード数超過時もスライドを複製して割当できるようにする
関連ブランチ: feat/rm089-flask-web-api
関連Issue: #454
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm089-flask-web-api を継続利用。新規ブランチなし。
    - 必ずmainからブランチを切る
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認待ち Plan を下に記載
    - 対象整理（スコープ、対象ファイル、前提）: SlideIdAligner が「カード数 > jobspec スライド数」でエラーになる問題を解消し、同一レイアウトのスライド複製を許可して全カードを割り当て可能にする。対象は `src/pptx_generator/pipeline/slide_alignment.py` と必要に応じて compose/テスト。API/CLI 共通の挙動を保つ。1カード=1スライドの原則は維持。
    - ドキュメント／コード修正方針: SlideIdAligner にクローン許可のオプションを導入し、競合や不足時にスライドを複製して新規 slide_id を払い出す。Meta に cloned_from など由来を残す。既存パス（カード<=スライド）を壊さない。必要なら OpenAPI/設計メモに挙動を追記。
    - 確認・共有方法（レビュー、ToDo 更新など）: チャット承認後に ToDo 更新、pytest 追加実行結果をメモ。必要に応じて notes 共有。
    - 想定影響ファイル: `src/pptx_generator/pipeline/slide_alignment.py`, `tests/api/test_flask_app.py` または pipeline テスト、compose 実装周辺。
    - リスク: slide_id 生成ルールの後方互換、クローン無限増殖防止、ログ/メタ肥大。ID 衝突を避ける命名規則を設ける。
    - テスト方針: cards>slides で全カード割当できること、cards=slides/cads<slides の既存ケースが壊れないことを pytest で確認。API/CLI フローの最小スモークを追加。
    - ロールバック方法: クローン関連のコミットを分離し、問題時に revert。
    - 承認メッセージ ID／リンク: （未記入）
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認後に具体案と ID ルールを追記
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
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。

## 参照済みドキュメント
- docs/policies/context-engineering.md
- CONTRIBUTING.md
- docs/policies/task-management.md
- docs/todo/template.md
