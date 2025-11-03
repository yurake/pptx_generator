---
目的: RM-046 生成AIブリーフ構成自動化の要件確認と実装準備を進め、段階的な deliverable を定義する
関連ブランチ: feat/rm046-brief-automation
関連Issue: #252
roadmap_item: RM-046 生成AIブリーフ構成自動化
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm046-brief-automation を main から作成し、`docs(todo): add rm046 kickoff todo` を初期コミットとして登録済み。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）
    - ドキュメント／コード修正方針
    - 確認・共有方法（レビュー、ToDo 更新など）
    - 想定影響ファイル
    - リスク
    - テスト方針
    - ロールバック方法
    - 承認メッセージ ID／リンク
    - Plan承認: ユーザー「ok」（2025-11-02 02:11 JST）
    - スコープ: RM-046「生成AIブリーフ構成自動化」の最終形に合わせて工程3の仕様を再設計し、現行設計との差分を整理する。既存挙動の互換維持は考慮せず、理想像への刷新を前提とする。
    - 影響ファイル: docs/requirements/stages/stage-03-content-normalization.md, docs/design/stages/stage-03-content-normalization.md, 必要に応じて docs/notes/, docs/roadmap/roadmap.md。
    - 前提・確認: 生成AIモード周辺（config/content_ai_policies.json, src/pptx_generator/content_ai/ など）の現状を把握し、RM-046 の期待成果（テンプレ依存ゼロの抽象ブリーフカード、HITL ログ方針）に照らして不足点を特定する。
    - 手順:
      1. 関連ドキュメント・コードから現状の生成AIフローと制約を洗い出し、RM-046 のゴールとギャップを一覧化する。
      2. ブリーフ入力フォーマット、生成カード構造、HITL ログ／承認フローの改訂案をまとめ、更新するドキュメント章立てを設計する。
      3. 了承後に進めるドキュメント改訂作業と、将来の実装タスク・検証方針・ロールバックシナリオを明文化する。
    - リスク: 他工程との整合（特に RM-047 以降）や未確定仕様の扱いが曖昧になること。保留事項はメモ化し次アクションを明確化する。
    - テスト方針: 本フェーズは仕様更新のみでテスト実施なし。実装フェーズで `uv run --extra dev pytest` 等を走らせる前提をドキュメントに記載する。
    - ロールバック: 変更ドキュメントを `git revert` で戻すか、差分を `git checkout` する。
    - 追記 (2025-11-02 14:05 JST): 工程4・5統合 `pptx compose` 機能の main 反映を前提に、`feat/rm046-brief-automation` への取り込み計画を以下の通り策定済み。後方互換は考慮不要で進める。
      - 作業範囲: main にマージされた compose 仕様を精査し、コード・CLI・パイプライン・ドキュメントの各レイヤーを刷新して RM-046 のブリーフ自動化フローへ統合する。
      - 想定更新ファイル: `src/pptx_generator/compose/*`, `src/pipeline/*`, `src/pptx_generator/cli/*`, `tests/test_cli_*`, `docs/requirements/`, `docs/design/`, `docs/runbooks/`, `README.md`, `docs/AGENTS.md`, 必要に応じて `config/`, `samples/`。
      - 進め方:
        1. main とブランチ差分を洗い出し、compose 統合による API・CLI・パイプラインの変更点と依存関係（.NET／LibreOffice 要件含む）を把握する。
        2. main を取り込みつつコンフリクトを解消し、compose 新仕様に合わせてコード・CLI エントリーポイント・パイプライン処理を更新する。
        3. テスト群と CI 設定を新仕様へ追従させ、`uv run --extra dev pytest` による全体テストと `uv run pptx compose ...` の実行確認を行う。
        4. ドキュメント（要件・設計・運用・README/AGENTS）を刷新し、手順・依存ツール・検証方法を現行仕様へ揃える。必要なら `docs/notes/` へ調査メモを残す。
        5. ToDo や関連資料へ結果を反映し、必要なら `docs/runbooks/` や `docs/policies/` を更新する。
      - リスク: compose 仕様との齟齬、CLI オプション互換性低下、テスト更新漏れ、サンプル・テンプレ不整合。
      - テスト戦略: `uv run --extra dev pytest`、`uv run pptx compose ...` の手動確認、LibreOffice ヘッドレス変換 (`soffice --headless --version`) のスポット確認。
      - ロールバック: 取り込みコミット単位で `git revert`、または再度 main からブランチを切り直す。
      - 承認: ユーザー「後方互換への考慮は不要。他については承認」メッセージ（2025-11-02 14:04 JST）。
- [x] 設計・実装方針の確定
  - メモ: `docs/notes/20251102-rm046-brief-analysis.md` に BriefCard への全面移行と実装ロードマップ／検証方針を整理済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点はユーザーへ相談した結果を残す
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: Brief 正規化パイプライン（`src/pptx_generator/brief/*`, `pipeline/brief_normalization.py`）および CLI 更新を実装済み。API のブリーフストア追加、テストの更新（`tests/test_cli_*` 等）も適用済み。今後の残タスクは RM-046 実装範囲に従って別途管理。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実行し 156 テスト通過。主要 CLI テスト（brief 入力、PDF、compose など）も緑化済み。
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

- [x] compose 統合対応
  - [x] main 差分の調査と依存ツール確認（.NET 8, LibreOffice, Open XML SDK）
    - メモ: origin/main に `pptx compose` 実装が未反映であることを確認し、既存ブランチの .NET 8 / LibreOffice 要件に追加変更がないことを再確認（`soffice --headless --version` は既存記録を参照）。
  - [x] main 取り込み／コンフリクト解消と compose 新仕様のコード反映
    - メモ: `src/pptx_generator/cli.py` へ `OutlineResult` ヘルパと `pptx compose` サブコマンドを追加し、`outline` / `mapping` の処理を共通化。`_run_mapping_pipeline` に既存ドラフトコンテキストを渡せるよう拡張。
  - [x] CLI・パイプライン・設定の更新（`uv run pptx compose` 系コマンド、入力 JSON、テンプレ参照）
    - メモ: Compose で `draft_*` と `rendering_ready.json` を一括生成する動線を実装し、`pipeline/__init__.py` に `BriefNormalization*` を再エクスポートして CLI 依存を解消。
  - [x] テスト更新と検証（`uv run --extra dev pytest`, `uv run pptx compose ...` 実行確認）
    - メモ: `tests/test_cli_integration.py::test_cli_compose_generates_stage45_outputs` を追加。`uv run --extra dev pytest tests/test_cli_integration.py` を実行し 30 ケース成功。手動で `uv run pptx compose` を走らせ、標準出力と生成物を確認。
  - [x] ドキュメント刷新（README, AGENTS, docs/requirements/, docs/design/, docs/runbooks/ 等）
    - メモ: README チートシート／工程解説、`docs/design/cli-command-reference.md`、`docs/runbooks/story-outline-ops.md` を compose 前提へ更新。既存要件ドキュメント（stage-04 mapping）との記述整合を再確認。
  - [x] 結果共有（ToDo/ドキュメント更新履歴の記録、必要に応じて docs/notes/ 追加）
    - メモ: 本報告（2025-11-02）で compose 実装内容と検証結果を共有。追加メモは当 ToDo と関連ドキュメントの更新履歴に集約。

## メモ
- 実装・テストは当コミットで完了済み。残課題としてドキュメント更新（README, roadmap 等）を別タスクで行う。
