---
目的: RM-072 slide_alignment 命名と責務の再整理
関連ブランチ: chore/rm072-slide-ai-rename
関連Issue: #328
roadmap_item: RM-072 slide_alignment 命名と責務の再整理
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 2025-11-27 chore/rm072-slide-ai-rename ブランチを main から作成し、本 ToDo 追加を初期コミットとして origin へ push 済み
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記する
    - 対象整理（スコープ、対象ファイル、前提）: 旧 `src/pptx_generator/content_ai/**` を `slide_ai/**` へ改名し、関連 import／公開 API／ロガー名／成果物を刷新。`config/content_ai_policies.json` は `config/slide_ai_policies.json` へ置換し、CLI・パイプライン・テスト・ドキュメントの参照を全て追従する。Slide ID 整合関連（`pipeline/slide_alignment.py` など）は新名称へ統一し、docstring やエラー文面も整理する。
    - ドキュメント／コード修正方針: コードと設定を段階的に rename しながら import 循環を抑止。成果物名やログが変わる箇所は運用ドキュメントも更新し、旧名称の痕跡を排除する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo 更新、Plan 承認メッセージの記録、PR で差分共有。必要に応じて docs/AGENTS.md ほか参照ドキュメントへリンクを追記。
    - 想定影響ファイル: `src/pptx_generator/content_ai/**` → `src/pptx_generator/slide_ai/**`, `src/pptx_generator/pipeline/slide_alignment.py`, `src/pptx_generator/cli.py`, `config/content_ai_policies.json` → `config/slide_ai_policies.json`, `tests/content_ai/**` → `tests/slide_ai/**`, `tests/test_slide_alignment.py`, 関連 docs (`docs/design/schema/stage-03-mapping.md`, `docs/notes/20251122-layout-ai-policy-review.md` 等)。
    - リスク: import 置換漏れで CLI や pytest が失敗、ポリシー JSON 名変更による既存ジョブとの不整合、監査ログの名称変更で運用が混乱する可能性。
    - テスト方針: `uv run --extra dev pytest tests/slide_ai`（rename 後のテスト群）、`uv run --extra dev pytest tests/test_slide_alignment.py`、必要に応じて `uv run --extra dev pytest tests/test_cli_integration.py -k slide`。
    - ロールバック方法: ブランチ `chore/rm072-slide-ai-rename` を破棄し、リモートブランチも削除して main を再取得する。
    - 承認メッセージ ID／リンク: （本スレッド直近の Plan 承認メッセージ）
- [x] 設計・実装方針の確定
  - メモ: モジュール／設定／テストの順にリネームし、公開 API とロガー、ポリシーを `slide_ai` 接頭辞へ統一する。既存フローは保持し、命名と参照のみ更新する方針で確定。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 追加メモは不要と判断。本 ToDo 記載内容で共有完了。
- [x] ドキュメント更新（要件・設計）
  - メモ: 設計ドキュメント内の `content_ai` 表記を `slide_ai` へ置換。要件文書は該当箇所が無いことを確認し、更新不要である旨を記録。
  - [x] docs/requirements 配下
    - メモ: 該当参照なしのため更新不要と判断。
  - [x] docs/design 配下
    - メモ: stage-02/03 設計資料のモジュール名・参照語を `slide_ai` へ更新。
- [x] 実装
  - メモ: モジュール・テスト・設定ファイルを `slide_ai` 命名へ統一し、ポリシー読込や SlideIdAligner の import を刷新。サンプルテキスト／ToDo など関連資産も併せて更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/slide_ai`, `tests/test_slide_alignment.py`, `tests/test_cli_integration.py -k slide` を実行し全件成功。
- [x] ドキュメント更新
  - メモ: ロードマップ・ポリシー・各種 ToDo を `slide_ai` 命名へ追従し、影響なしカテゴリについては更新不要と明記。
  - [x] docs/roadmap 配下
    - メモ: RM-064/072 セクションの記述を旧 `content_ai` から `slide_ai` へ更新。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: 要件文書に該当記述なしと確認し更新不要。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計資料のモジュール参照語を `slide_ai` へ統一。
  - [x] docs/runbook 配下
    - メモ: 影響なしと判断し更新不要を記録。
  - [x] README.md / AGENTS.md
    - メモ: 命名参照が無いため更新不要と確認。
- [x] 関連Issue 行の更新
  - メモ: 
- [x] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
