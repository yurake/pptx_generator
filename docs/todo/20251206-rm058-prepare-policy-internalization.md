---
目的: RM-058 プレペアポリシー内製化
関連ブランチ: feat/rm058-prepare-policy-internalization
関連Issue: #381
roadmap_item: RM-058 プレペアポリシー内製化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ `feat/rm058-prepare-policy-internalization` を main から作成済み。初期コミット `docs: record rm058 plan discussion` で ToDo/notes を追加し、この後 push 済み。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: stage2〜stage4 全体で `story_phase` を固定語彙に依存しない設計へ刷新し、`config/prepare_policies/default.json` を廃止する。`PrepareCardRole` などモデルを任意 intent ベースへ再設計し、既存互換は考慮しない。
    - ドキュメント／コード修正方針: 広範囲なコード改修（prepare CLI/handler/orchestrator、prepare_normalization、compose/mapping/layout/slide AI）と関連 docs 更新を一気に実施。旧成果物互換やフォールバックは提供しない。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認後に ToDo を逐次更新。大規模変更のため PR でまとめて共有。
    - 想定影響ファイル: `src/pptx_generator/prepare/models.py` を中心に stage2〜4 の Python モジュール全般、サンプル、テスト一式、`docs/requirements/stages/stage-02-prepare.md` ほか CLI/設計ドキュメント。
    - リスク: 互換性破壊による既存ワークフロー停止リスク。mapping/layout 推薦が新 intent ロジックで期待通り動作するか要検証。
    - テスト方針: `uv run --extra dev pytest` で CLI・パイプライン全体の更新テストを実行。story_phase 依存テストは全て新仕様へ書き換え。
    - ロールバック方法: 旧仕様へ戻す場合は本ブランチの変更を全 revert し、`config/prepare_policies/default.json` や旧モデル定義を復旧する。
    - 承認メッセージ ID／リンク: ユーザー承認メッセージ「ありがとう、planを承認しますので、todoのチェックを更新してcommit,pushして」
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
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
