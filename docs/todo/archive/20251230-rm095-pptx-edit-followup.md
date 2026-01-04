---
目的: RM-095 Stage5 PPTX 編集反映 フォローアップ（snapshot互換確認、Stage5適用パス実装、プロンプト整備、統合テスト追加）
関連ブランチ: feat/rm095-stage5-edit
関連Issue: #507
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm095-stage5-edit を継続利用（前タスクで作成・push 済み）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記。
    - 対象整理（スコープ、対象ファイル、前提）: snapshot 互換確認、Stage5 適用パス実装（並列 LLM→差分 JSON→シリアル書き込み）、指示フォーマット/プロンプト整備、統合テスト追加。
    - ドキュメント／コード修正方針: 互換影響を洗い出し、必要箇所のみ最小更新。適用パス実装で新規ヘルパを組み込み、README/ノートは結果を反映。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新とノート追記で共有。
    - 想定影響ファイル: analyzer/prompt生成/外部利用での slide_snapshot 参照箇所、Stage5 適用パスの実装ファイル、README/設計ドキュメント。
    - リスク: snapshot JSON 互換性変更の影響、LLM 適用パスでの誤反映、テスト不足。
    - テスト方針: 追加ユニット/統合テスト（指示→置換→出力）。最小ケースから追加。
    - ロールバック方法: 変更を粒度の小さいコミットで分割し revert 容易にする。
    - 承認メッセージ ID／リンク: 本スレッド「ok」
- [x] 設計・実装方針の確定
  - メモ: スライド単位で LLM を呼び出し、`--edits-json` 指定時は適用のみ。slide_index を付与して適用スコープを限定。並列LLM/スクショ連携は後続（RM-097）。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `pptx edit` に LLM 自動適用を追加（edits JSON なしで snapshot→LLM→適用）。手動適用は `--edits-json` で従来どおり。残タスク: (1) CLI E2E テスト追加、(2) プロンプト精緻化、(3) 並列LLM/スクショ連携は後置き（RM-097 でスクショ）。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/test_text_edit.py` 実行（6件成功）。実LLM（Azure OpenAI）で `samples/templates/edit_sample.pptx` をスライド単位で適用済み、ログで2回呼び出しと適用結果を確認。
- [x] ドキュメント更新
  - メモ: 今回の追加は適用スコープ修正とログ確認のみ。既存 README/ノートでカバーされており追記不要と判断。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（影響なし）
  - [x] docs/requirements 配下（影響なし）
  - [x] docs/design 配下（影響なし）
  - [x] docs/runbook 配下（影響なし）
  - [x] README.md / AGENTS.md（影響なし）
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: 残タスクは PR 作成のみ。
- [x] PR 作成
  - メモ: PR #525 https://github.com/yurake/pptx_generator/pull/525（2026-01-03 完了）

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: Stage5 フォローアップ。slide_snapshot 互換性に注意（parent_shape_id/table_cell）。
  - 決定と理由: table_cell_shape_id を公開し、テーブルセルへのテキスト置換を shape_id 基準で扱う方針。text_edit に書式維持での apply_shape_text_edits を追加して差分適用基盤とする。
  - リスク(UNCONFIRMED): LLM 出力のマッピング漏れ、プロンプト精度不足。スクリーンショット連携は未対応（RM-097へ後送り）。
  - Now/Next: Now=LLM 自動適用実装完了（edits JSON なしで snapshot→LLM→適用）。Next= (1) CLI E2E テスト追加、(2) プロンプト精緻化、(3) スクショ連携は RM-097 で対応。
  - テスト実績/抜け: `uv run --extra dev pytest tests/pipeline/test_text_edit.py` (4件成功)。CLI/E2E 未実施。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
