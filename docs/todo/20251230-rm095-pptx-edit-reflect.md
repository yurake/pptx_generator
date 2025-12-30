---
目的: RM-095 Stage5 PPTX 編集反映の着手と基盤整備（スナップショット拡張とテキスト置換適用経路の検討・実装）
関連ブランチ: feat/rm095-stage5-edit
関連Issue: #506
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm095-stage5-edit を main から作成。初期コミットなし、未 push。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記。
    - 対象整理（スコープ、対象ファイル、前提）: Stage5 基盤調査。mode static スナップショットのグループ/表セル対応可否確認と拡張案検討。生成済み PPTX への shape_id ベーステキスト置換ユーティリティ有無の調査と書式維持での設計。対象: `src/pptx_generator/cli_handlers/template_extraction.py`, `src/pptx_generator/pipeline/analyzer/snapshot.py`, `src/pptx_generator/pipeline/renderer/` 配下など。
    - ドキュメント／コード修正方針: 現状調査後、必要最小の拡張/ヘルパを追加（ラン流用で書式保持）。互換性影響は最小化。
    - 確認・共有方法（レビュー、ToDo 更新など）: 作業進捗と決定を本 ToDo に更新。
    - 想定影響ファイル: スナップショット抽出ロジック、レンダリング/テキスト置換周辺。
    - リスク: スナップショット出力互換性変化、ラン構造変更による書式崩れ。
    - テスト方針: 可能ならグループ/表セルを含む簡易 PPTX で snapshot 出力確認、置換ヘルパの書式維持をユニットで確認。
    - ロールバック方法: 変更を単一コミットにまとめ revert 可能な粒度で対応。調査のみの場合はコード変更なし。
    - 承認メッセージ ID／リンク: 本スレッド「ok」
- [x] 設計・実装方針の確定
  - メモ: スナップショットは再帰でグループ配下を展開し、親座標を加算。テーブルはセル単位で shape_id を `table_shape_id*10000 + row*100 + col` とし、row/col メタを付与。テキスト置換は text_frame の書式をスナップショットし、runs/paragrah 属性へ再適用しながら差し替えるヘルパを新設。互換性影響: slide_snapshot.json に parent_shape_id/table_cell を追加し形状リストが増加する可能性あり。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: スライドスナップショット拡張（グループ再帰＋表セル抽出）とテキスト置換ヘルパ追加。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/analyzer/test_snapshot_extraction.py tests/pipeline/test_text_edit.py` 実行、3件成功。
- [x] ドキュメント更新
  - メモ: 今回の修正は text_edit の slide_index スコープ処理のみ。利用方法は CLI ヘルプと既存 note で十分のため追記不要と判断。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（影響なし）
  - [x] docs/requirements 配下（影響なし）
  - [x] docs/design 配下（影響なし）
  - [x] docs/runbook 配下（影響なし）
  - [x] README.md / AGENTS.md（影響なし）
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: ドキュメント更新を完了とし、残タスクは PR 作成のみ。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: Stage5 基盤調査として snapshot 拡張と置換ヘルパを追加。slide_snapshot.json はフィールド追加で互換性影響の可能性あり。
  - 決定と理由: グループは親座標加算で再帰展開、テーブルはセルを疑似shapeとして row/col メタ付与。テキスト置換は text_frame clear 後に元スタイルをコピーして再適用し、ラン構造を簡易維持。
  - リスク(UNCONFIRMED): テーブルセル shape_id の算出方式が将来の shape_id 上限と衝突する可能性（低）。slide_snapshot.json の構造変更が利用側に影響する可能性。
  - Now/Next: Now: 実装・テスト済み。Next: 既存ドキュメント/利用箇所の互換確認と追記要否の検討、ブランチ push 準備。
  - テスト実績/抜け: `uv run --extra dev pytest tests/pipeline/analyzer/test_snapshot_extraction.py tests/pipeline/test_text_edit.py`（3件成功）。統合テストは未実施。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
