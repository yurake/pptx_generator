---
目的: RM-097 Stage5 スクリーンショット生成 / edit 画像入力対応
関連ブランチ: feat/rm097-edit-image-input
関連Issue: #567
roadmap_item: RM-097 Stage5 スクリーンショット生成
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-27: feat/rm097-edit-image-input を作成。初期コミット=a2e9c34（ToDo追加）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提): Stage5 edit のみに画像入力を追加。PPTX→スライド画像生成＋LLM入力の共通レイヤーを実装し、非対応プロバイダはテキストのみフォールバック。対象は pipeline/edit_runner.py、pipeline/text_edit.py、edit_ai/client.py、edit_ai/prompts.py、cli_commands/edit.py、api/stages.py、設定/ユーティリティ（画像生成）。画像は複数形式（png/jpeg等）に対応。
    - ドキュメント／コード修正方針: RM-097 の位置づけに沿って Stage5 前処理として画像生成を追加。LLM入力は provider 依存を最小化し、共通の payload builder から各プロバイダへ変換。画像未対応はテキストのみで挙動維持。画像の保存先は出力ディレクトリ配下に統一する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo に進捗/結果を記録し PR 本文へテスト/UAT結果を記載。
    - 想定影響ファイル: edit_runner.py、text_edit.py、edit_ai/client.py/prompts.py、cli_commands/edit.py、api/stages.py、新規画像生成ユーティリティ、tests/edit_ai・tests/pipeline。
    - リスク: LibreOffice 依存（環境差/タイムアウト）、画像サイズ増によるLMM遅延、プロバイダ非対応時のフォールバック品質。
    - テスト方針: 画像生成ユーティリティの単体テスト、edit runner 統合テスト（画像あり/なし）、`uv run --extra dev pytest tests/edit_ai/test_client_providers.py -k edit`、`uv tool run diff-cover coverage.xml --compare-branch upstream/main`。
    - ロールバック方法: 画像生成と LLM入力の追加パスを revert し、従来の text-only に戻す。
    - 承認メッセージ ID／リンク: 2026-01-27 ユーザー承認「OK」
- [x] 設計・実装方針の確定
  - メモ: Stage5 edit の前処理でスライド画像を生成し、LLM 入力に画像＋shape 座標を付与する。画像入力は `PPTX_EDIT_IMAGE_INPUT=1` で有効化し、未指定時はテキストのみで既存挙動を維持する。画像は `images/` 配下に保存し、`edit_slide_images.json` に PPTX/スライド/shape の対応メタを記録する。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
    - docs/notes/20260127-rm097-edit-image-input.md
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: 画像生成ユーティリティ（slide_image_exporter）追加、edit LLM 入力に画像＋座標メタを付与、スクリーンショットメタ保存、環境変数で有効化する分岐を追加。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト: 実行コマンドと結果（例: `uv run --extra dev pytest`, `diff-cover`）
    - ユーザー経路の手動確認（必要な場合）: 代表手順1本のコマンドと結果
    - 生成物の確認があれば、その方法と結果
    - 自動テスト:
      - `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/pipeline/test_slide_image_exporter.py tests/pipeline/test_edit_runner_images.py tests/edit_ai/test_client_providers.py --cov=src/pptx_generator --cov-report=xml`
        - 結果: 10 passed（coverage.xml 生成）
      - `UV_CACHE_DIR=.uv-cache uv tool run diff-cover coverage.xml --compare-branch upstream/main`
        - 結果: Coverage 83%
    - ユーザー経路の手動確認（UAT）:
      - `UV_CACHE_DIR=.uv-cache PPTX_LLM_PROVIDER=mock PPTX_EDIT_IMAGE_INPUT=1 PPTX_EDIT_IMAGE_FORMATS=png uv run --extra dev pptx edit samples/templates/edit_sample.pptx --output .pptx/uat-rm097/edit_sample.pptx`
        - 結果: `soffice` 未導入のためスクリーンショット生成はスキップ（警告出力）。PPTX 出力と `applied_edits.json` を生成、`.pptx/uat-rm097/images/` は空。
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（RM-097 の参照ドキュメントを追加）
  - [x] docs/requirements 配下（stage-05-edit / requirements 反映）
  - [x] docs/design 配下（stage-05-edit / schema 反映）
  - [x] docs/runbook 配下（変更なし: 運用手順の追加なし）
  - [x] README.md / AGENTS.md（変更なし: CLI/運用の追記なし）
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` を `#567` に更新。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約:
  - 決定と理由:
  - リスク(UNCONFIRMED):
  - Now/Next: テスト・検証まで完了。次はPR準備。
  - テスト実績/抜け: uv 再インストール後に pytest と diff-cover 実行済み。UAT は mock で edit 実行、LibreOffice 未導入のため画像生成はスキップ。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
