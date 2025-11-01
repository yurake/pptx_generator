---
目的: 工程4+5の統合CLIラッパー仕様策定と実装準備
関連ブランチ: feat/rm048-cli-wrapper
関連Issue: #253
roadmap_item: RM-048 工程4+5 統合CLI整備
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm048-cli-wrapper を main から作成し、本 ToDo を初期コミットとして追加。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ:
    - スコープ
      - CLI に工程4+5を連続実行する新サブコマンド（名称: compose）を追加し、`outline` → `mapping` の再実行を一括化する。
      - 共通入出力（spec／ドラフト出力／rendering_ready）とブランド・テンプレート指定の扱いを整理し、必要なガイド更新を行う。
      - 失敗時のロールバックとログ出力方針を定義し、既存コマンドとの互換性を維持する。
    - 影響ファイル（想定）
      - `src/pptx_generator/cli.py`: サブコマンド追加と共通ユーティリティ抽出。
      - `src/pptx_generator/pipeline/...`: 必要に応じて補助関数追加。
      - `tests/test_cli_integration.py`: 新サブコマンドの統合テスト。
      - `docs/design/design.md`・`docs/runbooks/`: 新コマンド仕様と運用手順の追記。
      - `docs/roadmap/roadmap.md`: 成果反映。
    - 実施ステップ
      1. 既存 `outline` / `mapping` の必須引数・成果物の依存関係を整理し、ラッパーの入出力フローと失敗時の扱いを仕様化（ドキュメント草案作成）。
      2. CLI 実装：共通の spec ロード・ドラフト出力パス・rendering_ready 出力先を制御しつつ、両コマンドを連続実行するサブコマンドを追加。必要なら共通関数を抽出。
      3. 統合テストを追加し、正常系で `.pptx/draft` と `.pptx/gen` の成果物が揃うこと、途中失敗時に exit code が伝播することを検証。
      4. 運用ドキュメント更新：新コマンドの使用例、既存 `pptx gen` との役割分担、再実行手順を `docs/runbooks/` 等へ反映し、ロードマップ進捗を更新。
      5. テスト実行 (`uv run --extra dev pytest tests/test_cli_integration.py` など) と CLI ヘルプ確認 (`uv run pptx --help`)、必要に応じ `uv run pptx compose ... --export-pdf` などオプション連携を確認。
    - リスク・前提
      - 既存コマンドが想定する出力ディレクトリ構成との齟齬。
      - 追加オプションのバリエーションをどこまでサポートするか（当面は代表的なものに限定し、将来拡張余地をドキュメント化）。
      - LibreOffice やテンプレート依存で所要時間が伸びる可能性。必要なら `--skip-pdf` など透過設定を検討。
    - テスト戦略
      - 新統合テストでの CLI 実行結果確認。
      - 既存 CLI テスト群のリグレッション (`uv run --extra dev pytest tests/test_cli_integration.py tests/test_cli_outline.py tests/test_cli_content.py`)。
      - 任意で `uv run pptx compose ... --export-pdf` を実ファイルで試行。
    - ロールバック方針
      - 新サブコマンドと関連ドキュメント／テストを削除し、`docs/roadmap` と ToDo の該当記述を元に戻す。
      - 既存 `outline` / `mapping` には変更を加えない設計とし、個別コマンド単体利用への影響を最小化。
    - 承認メッセージ ID／リンク: user-ok-20251102
- [ ] 設計・実装方針の確定
  - メモ: 未着手
- [ ] ドキュメント更新（要件・設計）
  - メモ: 未着手
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 未着手
- [ ] テスト・検証
  - メモ: 未着手
- [ ] ドキュメント更新
  - メモ: 未着手
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 未着手
- [ ] PR 作成
  - メモ: 未着手

## メモ
- 
