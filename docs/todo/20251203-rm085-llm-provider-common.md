---
目的: RM-085 LLM プロバイダ共通化
関連ブランチ: feat/rm085-llm-provider-common
関連Issue: 未作成
roadmap_item: RM-085 LLM プロバイダ共通化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: `feat/rm085-llm-provider-common` を作成し、このブランチ上で作業中
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan（2025-12-03 ユーザー承認）を転記
    - 対象整理（スコープ、対象ファイル、前提）: `slide_ai` / `prepare_ai` / `layout_ai` / `template_ai` の `create_*_client` を共通ヘルパーに切り替え、CLI ロガーも同じ解決ロジックを利用する。
    - ドキュメント／コード修正方針: 新規 `pptx_generator.llm` パッケージを追加し、既存ファクトリとテストを同ヘルパー経由に統合。ロードマップと ToDo を更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo へ進捗を記録し、Plan 承認 ID を残す。
    - 想定影響ファイル: `docs/roadmap/roadmap.md`, `docs/todo/*`, `src/pptx_generator/llm/**`, `src/pptx_generator/{slide_ai,prepare_ai,layout_ai,template_ai}/client.py`, `src/pptx_generator/cli_handlers/common.py`, 関連テスト。
    - リスク: 既存プロバイダ別の分岐挙動が変わる可能性、環境変数エイリアスの互換性、遅延インポートによる副作用。
    - テスト方針: 既存ユニットテスト更新に加えて新規ヘルパーの単体テストを作成し、`pytest` で対象モジュールを実行。
    - ロールバック方法: 新規 `pptx_generator.llm` モジュールと関連修正を revert し、各 `create_*_client` を元の環境変数分岐に戻す。ドキュメントも同時に戻す。
    - 承認メッセージ ID／リンク: 2025-12-03 ユーザー応答「ok」
- [x] 設計・実装方針の確定
  - メモ: `resolve_llm_provider` で環境変数→プロバイダ名の正規化とソース追跡を行い、各 client ファクトリは辞書ベースでインスタンス生成。Template AI は専用オーバーライド環境変数に対応し、CLI ロガーも同ヘルパーを利用する。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `src/pptx_generator/llm/provider.py` を新設し、Slide/Prepare/Layout/Template 各 client と CLI ロガーを共通ヘルパー利用へリファクタリング。`prepare_ai/__init__.py` は遅延インポート化。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/llm/test_provider_resolution.py tests/slide_ai/test_client_factory_initialization.py tests/prepare_ai/test_prepare_ai_llm_client_configuration.py`
- [x] ドキュメント更新
  - メモ: RM 追記と ToDo 更新を実施
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 未作成
- [ ] チェックリスト整合確認
  - メモ: Final チェック時に更新
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 
