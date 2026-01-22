---
目的: RM-085 LLM プロバイダ共通化（aws-claude の全ステージ対応と JSON 解析互換を確保する）
関連ブランチ: fix/rm085-aws-claude-json
関連Issue: 未作成
roadmap_item: RM-085 LLM プロバイダ共通化  # 既存 RM を指定。未登録テーマの場合はロードマップへ RM を追加してから記入する。
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - ブランチ: fix/rm085-aws-claude-json（origin/main から作成）
    - 初期コミット: dc8ceb5 chore: add rm085 aws-claude json todo
    - push: origin/fix/rm085-aws-claude-json へ push 済み
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: aws-claude のコードフェンス付き JSON を全ステージで受け付ける共通パース追加、prepare_ai に aws-claude 対応を追加して stage1〜5 を通せるようにする。
    - ドキュメント／コード修正方針: 既存 JSON パーサ前段にコードフェンス除去/JSON 抽出の共通関数を追加し、Template/Prepare/Slide/Layout の AI 結果処理に適用。prepare_ai/client.py で Bedrock (aws-claude) を有効化。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新と CLI 簡易再実行で挙動を確認する。
    - 想定影響ファイル: src/pptx_generator/prepare_ai/client.py, src/pptx_generator/llm/*, src/pptx_generator/template_ai/*, src/pptx_generator/layout_ai/*, src/pptx_generator/slide_ai/* など。
    - リスク: パースを緩めすぎて不正 JSON を通す可能性。抽出後に JSON デコード失敗は従来通りエラーとし、厳格さを維持する。
    - テスト方針: 文字列パースの単体テスト追加（コードフェンス/前後ノイズ）。可能なら uv run pptx template ... --mode dynamic などの CLI で再現確認。
    - ロールバック方法: 共通パーサ追加と prepare_ai の aws-claude 対応コミットを revert する。
    - 承認メッセージ ID／リンク: 2026-01-22 ユーザー OK
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
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: aws-claude がコードフェンス付き JSON を返すため、JSON のみ期待のパーサが失敗している。
  - 決定と理由: コードフェンス除去/JSON 抽出の共通前処理を追加してプロバイダ差分を吸収する。
  - リスク(UNCONFIRMED): 抽出ロジックの過度な緩和で想定外入力を通す可能性。
  - Now/Next: 設計方針確定 → 実装 → テスト。
  - テスト実績/抜け: 未実施。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
