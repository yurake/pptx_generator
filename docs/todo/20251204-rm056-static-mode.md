---
目的: RM-056 多形式インポート 静的モード対応検証と実装
関連ブランチ: feat/rm056-cli-integration
関連Issue: #364
roadmap_item: RM-056 多形式インポートCLI統合
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ `feat/rm056-cli-integration` を継続利用する（新規作成なし）
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: `pptx prepare --mode static` で PDF/HTML/URL/data URI を ContentImportService 経由で取り込み、Stage3/Stage4 まで import_sources を維持。既存 jobspec を前提に `feat/rm056-cli-integration` ブランチで対応。
    - ドキュメント／コード修正方針: `cli_handlers/prepare.py` 静的分岐の入力正規化を拡張、必要なら `prepare/models.py` を補強。CLI 静的モードの手順を CLI リファレンスなどに追記。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo で進捗を記録し、完了時は PR に ToDo を添付。ユーザーと Plan→実装→テスト結果を共有。
    - 想定影響ファイル: `src/pptx_generator/cli_handlers/prepare.py`, `prepare/models.py`, `tests/cli/test_cli_prepare_stage_flow.py`, 静的 UAT 用テスト、関連 docs。
    - リスク: jobspec 依存で入力正規化のズレが発生する恐れ。LibreOffice 変換の失敗や静的コンテキストとの整合性不足。
    - テスト方針: pytest で静的モード用ケース追加、手動で `prepare --mode static` → `compose` → `gen` を通し `import_sources` を確認。
    - ロールバック方法: 静的モード対応コミットと docs/テスト追加を revert する。
    - 承認メッセージ ID／リンク: ユーザー「ok」(2025-12-04)
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
  - メモ: 静的検証用に `.pptx/slide_inputs.md` を全スライド分埋め直し（samples/input の Markdown/HTML/PDF/TXT を割当）。コード差分は未コミット。
- [x] テスト・検証
  - メモ: 実施したテスト内容と結果を記入する
  - メモ: `uv run --extra dev pptx template samples/templates/templates.pptx --layout-mode static` を再実行し Stage1 リソースを更新（warnings=0）。
  - メモ: `uv run --extra dev pptx prepare --mode static --jobspec .pptx/extract/jobspec.json --output .pptx/prepare` を実施し、`import_sources` 25 件（structured 16 / content_import 8 / template_spec 1）、slot coverage 必須112/112・任意23/23を確認。
  - メモ: `uv run --extra dev pptx compose .pptx/extract/jobspec.json --prepare-cards .pptx/prepare/prepare_card.json` で `generate_ready.json` / `generate_ready_meta.json` を生成し、`mode=static` と Blueprint 情報が継承されていることを確認。
  - メモ: `uv run --extra dev pptx gen .pptx/compose/generate_ready.json --output .pptx/gen --export-pdf` を完走（LibreOffice 変換成功）。`rendering_log.json` で空プレースホルダー警告 83 件、Monitoring alert 24 件が出力されているため別途原因整理が必要。
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
