---
目的: RM-093 入力配置規約の着手準備と入出力パス規約策定・実装方針整理
関連ブランチ: feat/rm093-input-placement
関連Issue: #443
roadmap_item: RM-093 入力配置規約
---

- [x] ブランチ作成・初期コミット・push
  - メモ: `feat/rm093-input-placement` を main から作成済み。初期コミット（ToDo 追加）をコミットし push 済み。upstream を origin/feat/rm093-input-placement に設定。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記。
    - 対象整理（スコープ、対象ファイル、前提）: Web/API 専用で入力配置規約を導入。CLI 既定入力は非対象（RM-092 と同じ分界）。tx/job 未指定リクエストはサーバで tx を初回発行し、毎リクエスト job を発行してから入力ディレクトリを決定。パス規約は `PPTX_INPUT_ROOT/<transaction_id>/<job_id>/`。`PPTX_INPUT_ROOT` 未指定時は `.pptx/input`（API 内部のみ）。
    - ドキュメント／コード修正方針: `settings/paths.py` に入力ルートヘルパー追加（get_input_root/build_input_dir 想定）と tx/job 付きパス組み立て実装。CLI には組み込まない。ドキュメントは README / docs/design/cli/cli-command-reference.md に Web/API 専用の入力配置と既定値を追記。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo を随時更新。実装後に差分レビューを想定。
    - 想定影響ファイル: `src/pptx_generator/settings/paths.py`, `tests/settings/*`（新規追加予定）, `README.md`, `docs/design/cli/cli-command-reference.md`。
    - リスク: CLI 互換性リスクはゼロに抑える（非適用）。tx/job 未指定処理漏れに注意。パス生成のみのため副作用は限定的。
    - テスト方針: 環境変数有無・tx/job 有無のパス組み立て単体テストを追加し `uv run --extra dev pytest tests/settings/test_input_paths.py` を想定。
    - ロールバック方法: 入力パス解決追加のコミットを revert する。
    - 承認メッセージ ID／リンク: 本スレッド
- [x] 設計・実装方針の確定
  - メモ: Plan 承認内容どおり、Web/API 専用の入力配置解決ヘルパーを追加し CLI は非変更とする方針で実装。追加の設計メモ共有は不要。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `settings/paths.py` に `get_input_root` / `build_input_dir` を追加し、入力配置の tx/job 付き組み立てを実装。出力関連コードや CLI は非変更。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/settings/test_input_paths.py` 実行（3 件成功、coverage.xml 更新）。
- [x] ドキュメント更新
  - メモ: README に `PPTX_INPUT_ROOT` / `PPTX_OUTPUT_ROOT` のパス規約とデフォルトを追記。CLI リファレンスに入力配置（Web/API 専用）を明記。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（変更不要: 本実装はロードマップ本文に影響なし）
  - [x] docs/requirements 配下（変更不要: 要件定義への影響なし）
  - [x] docs/design 配下（CLI リファレンスを更新済み）
  - [x] docs/runbook 配下（変更不要: 運用手順への影響なし）
  - [x] README.md / AGENTS.md（README を更新、AGENTS は変更不要）
- [x] 関連Issue 行の更新
  - メモ: 
- [x] チェックリスト整合確認
  - メモ: PR 作成のみ未着手。その他項目は完了。
- [x] PR 作成
  - メモ: PR #445 https://github.com/yurake/pptx_generator/pull/445（2025-12-18 完了）

## メモ
-
