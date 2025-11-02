---
目的: 工程4+5の統合CLIラッパー仕様策定と実装準備
関連ブランチ: feat/rm048-cli-wrapper
関連Issue: #253
roadmap_item: RM-048 工程4+5 統合CLI整備
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm048-cli-wrapper を main から作成し、本 ToDo を初期コミットとして追加。
- [x] 計画策定（スコープ・前提の整理）
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
- [x] 設計・実装方針の確定
  - メモ: `compose` サブコマンドで工程4のドラフト生成と工程5のマッピングを連続実行する。`cli.py` にアウトライン／マッピング共通の内部ヘルパー（`_execute_outline` / `_execute_mapping`）を追加し、既存コマンドからも再利用することで挙動の一貫性を担保する。ドラフト成果物のメタ出力と layout スコア表示は共通化し、エラーコードは既存 CLI と同一になるよう整理する。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/design/20251019-stage3-4-cli.md` に compose CLI 追加方針を追記。要件定義への影響はなく `docs/requirements` は現状維持。
  - [x] docs/requirements 配下（変更なしを確認）
  - [x] docs/design 配下
- [x] 実装
  - メモ: `src/pptx_generator/cli.py` に `_execute_outline` / `_execute_mapping` を追加し、`compose` サブコマンドを実装。`outline` / `mapping` コマンドも新ヘルパーを利用するよう改修。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_integration.py` を実行し、`test_cli_compose_generates_stage45_outputs` を含む30ケースが成功。
- [x] ドキュメント更新
  - メモ: `docs/design/cli-command-reference.md` に compose を追記し、`docs/runbooks/story-outline-ops.md` の工程手順を更新。`docs/roadmap/roadmap.md` で RM-048 を進行中へ更新し、`docs/requirements` は影響なし。README には追記準備中のため別途検討。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認：影響なし）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md（README に compose を追記、AGENTS は変更不要）
  - 追加対応計画:
    - スコープ
      - 工程体系を 6 → 5 工程へ変更し、従来の工程4/5（ドラフト構成・マッピング）を統合して新しい「工程4: マッピング」と定義し直す。
      - README は新工程4を基準に簡潔化し、旧工程4/5の細部は既存の詳細ドキュメントへ退避／集約する。
      - requirements/design など工程別ドキュメントを統合・改訂し、工程番号と呼称を全体で整合させる。
    - 影響ドキュメント（想定）
      - `README.md`（工程一覧・チートシート等の更新）
      - `docs/requirements/stages/*.md`（stage-04/05 の統合 → 新 stage-04）
      - `docs/design/*`（工程解説・CLI 記述の工程番号更新）
      - `docs/runbooks/`, `docs/notes/` など工程数に言及する箇所全般
      - ToDo / roadmap の記録更新（必要なら）
    - 実施ステップ
      1. 工程に関するドキュメントを洗い出し、6工程前提の記述箇所を一覧化。
      2. requirements/design の工程4/5 ドキュメントを統合し、新工程4「マッピング」として構成・内容を再整理。
      3. README から旧工程4/5 詳細を削除し、新工程4概要と該当ドキュメントへの導線を記載。
      4. それ以外の資料（設計書・runbook・notes・CLI リファレンス等）の工程数・名称・参照リンクを 5 工程体制に合わせて更新。
      5. 変更箇所を確認し、必要に応じて diff チェックと表記揺れの統一を実施。
    - リスク・前提
      - 工程番号変更に伴う参照リンク切れ（目次・アンカー等）が発生し得る。
      - ドキュメント間で工程呼称が混在する可能性があるため、統一ルールの適用が必要。
      - CLI やツール側の挙動は変更しない前提で、ドキュメントのみを更新する。
    - テスト戦略
      - 自動テストは不要。ドキュメント校正（リンク確認・lint/markdown チェックがあれば実行）を想定。
    - ロールバック方法
      - 統合前のドキュメント（旧 stage-04/05）を git revert で復元し、README 等の工程数表記を 6 工程に戻す。
    - 調査メモ
      - README.md: 工程数紹介、Mermaid 図、CLI チートシート、工程別ガイド概要、補足コメント。
      - docs/design/design.md / cli-command-reference.md / 20251019-stage3-4-cli.md / rm005-story-modeler.md など、工程3/4/5 を明記している設計資料。
      - docs/requirements/stages/stage-04-mapping.md および対応する design/stages ファイル。
      - docs/runbooks/story-outline-ops.md、support.md、pptx-analyzer.md など工程を参照する運用手順。
      - docs/notes/20251011-roadmap-refresh.md、20251012-readme-refactor.md、20251019-rm033-scope.md 等、6 工程を前提としたノート。
      - その他 `docs/AGENTS.md`、ロードマップ、ToDo 等に散在する「工程3/4」「工程5/6」表現。
- [x] 関連Issue 行の更新
  - メモ: #253 を参照先 Issue として設定済み。
- [ ] PR 作成
  - メモ: 未着手

## メモ
- 
