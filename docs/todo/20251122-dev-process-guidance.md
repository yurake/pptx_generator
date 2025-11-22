---
目的: 開発プロセス運用ルール（ToDo と RM の連携、ブランチ命名、ロードマップ更新手順）の見直しと改善方針の策定、および RM-069 の新規登録準備
関連ブランチ: docs/rm069-dev-process-guidance
関連Issue: #299
roadmap_item: RM-069 開発プロセス運用ルール見直し
---

- [x] ブランチ作成と初期コミット
  - メモ: `docs/rm069-dev-process-guidance` を `main` から作成し、ToDo 追加のみを初期コミット（84e02a6, 4e9e343）で記録済み。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: 
      - 既に作成済みの `docs/todo/20251122-dev-process-guidance.md` と、今後更新対象となる `AGENTS.md` / `docs/policies/task-management.md` / `docs/todo/template.md` / `docs/todo/README.md` / `docs/roadmap/roadmap.md` / `docs/roadmap/` 配下の関連ドキュメント、`scripts/auto_complete_todo.py` や `scripts/lint_todo_completion.py` など自動化スクリプト。  
      - 先行して作ってしまったコミット（`84e02a6` / `4e9e343` / `6ae6482`）は見直し対象とし、承認後の方針に沿うよう必要なら修正・再コミットまたは `git revert` で戻す。
    - ドキュメント／コード修正方針: 
      1. ToDo・ロードマップ・ブランチ命名まわりの運用ルールを整理し、`AGENTS.md` と関連ポリシー文書・テンプレに反映。  
      2. ロードマップへ新規 `RM-069` を追加し、Mermaid 図や個別セクションに整合性を持たせる。  
      3. `todo-auto-complete` などのスクリプトで完了済み RM の扱い、`RM-000` の特例、`prefix/rmxxx-slug` 命名ルールが整合するか確認し、必要な調整を行う。  
      4. 既存 ToDo／ドキュメントで新ルールに反する箇所があれば追随する。今回先行作成した ToDo も Plan 承認後の内容に合わせて刷新する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 
      - ドキュメント差分はコミット単位で説明可能な状態に整理。  
      - ToDo の「計画策定」欄へ本 Plan を転記。  
      - 変更内容は最終返信で一覧化し、必要に応じて `docs/todo/20251122-dev-process-guidance.md` のメモにも結果を記録。
    - 想定影響ファイル: 
      - `AGENTS.md`、`docs/policies/task-management.md`、`docs/todo/template.md`、`docs/todo/README.md`、`docs/roadmap/roadmap.md`、`scripts/auto_complete_todo.py`、`scripts/lint_todo_completion.py`、関連テスト（`tests/test_auto_complete_todo.py` 等）、`docs/todo/20251122-dev-process-guidance.md` 自身。
    - リスク: 
      - 自動化スクリプトの想定外変更で ToDo アーカイブ／ロードマップ更新が壊れる恐れ。→ 単体テストやドライランで挙動確認。  
      - Mermaid 図やロードマップ編集ミス。→ 既存記法を踏襲し diff をレビュー。  
      - 既存 ToDo との整合が崩れ lint が失敗するリスク。→ `scripts/lint_todo_completion.py` 実行で検証。
    - テスト方針: 
      - ドキュメント変更は目視確認と `git diff` でチェック。  
      - スクリプトを変更する場合、既存テスト（`pytest tests/test_auto_complete_todo.py` 等）を `uv run --extra dev pytest ...` で実行。  
      - 追加で `uv run python scripts/lint_todo_completion.py`（必要なら対象指定）で lint 動作確認。
    - ロールバック方法: 
      - 認識違いがあった場合は該当コミットを `git revert` で戻すか、承認済み方針に沿って再編集する。  
      - 先に作成した 3 コミットを元に戻す必要があれば、`git revert 84e02a6 4e9e343 6ae6482` を順に実行し ToDo を作り直す。
    - 承認メッセージ ID／リンク: ユーザーメッセージ「では作業に戻って」
- [x] 設計・実装方針の確定
  - メモ: ToDo／ロードマップ連携の統一（既存 RM 必須 + lint）、ブランチ命名ルールの `prefix/rmxxx-slug` 統一、RM 採番プロセスの明文化、Issue 連携での RM 表示強化、Mermaid 図から完了テーマを除外する自動化改善を実施する方針でユーザー合意済み。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 本 ToDo の「## メモ」に現状確認と対応方針を全文記録済み。追加ドキュメントは不要と判断。
- [x] ドキュメント更新（要件・設計）
  - メモ: 今回は運用ポリシー／テンプレ更新のみで要件・設計ドキュメントの内容に影響なし。変更不要である旨を記録。
  - [x] docs/requirements 配下
    - メモ: 対象機能に要件差分なし（運用ルール更新のみ）。
  - [x] docs/design 配下
    - メモ: 設計仕様への反映不要（プロセス自体の更新に留まる）。
- [ ] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_auto_complete_todo.py tests/test_lint_todo_completion.py` を実行し、Mermaid ノード除外と lint 強化の回帰確認を実施（8 件成功）。
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [x] docs/roadmap 配下
    - メモ: `docs/roadmap/roadmap.md` に RM-069 を追加し、Mermaid 図から完了テーマを除外する構成へ更新。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: 対象要件文書に変更点なし（プロセス改善のみのため更新不要）。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計ドキュメントには差分が発生しないことを確認。
  - [x] docs/runbook 配下
    - メモ: ランブック系手順への影響なし。更新不要を確認。
  - [x] README.md / AGENTS.md
    - メモ: `AGENTS.md` と `docs/todo/README.md` に親子タスクのチェック運用と RM 紐付けルールを追記。
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] 開発プロセス課題の現状整理
  - [x] ToDo と RM の紐付けルール現状確認
  - [x] ブランチ命名ルール現状確認
  - [x] RM 番号採番プロセス現状確認
  - [x] ToDo 目的欄・Issue での RM 表記現状確認
  - [x] Mermaid 図での完了扱い現状確認
  - メモ: 上記 5 点の現行状態と課題、対応方針をユーザーへ共有済み（承認前 Plan の一部として整理）。
- [x] 対応方針のチケット化・追跡
  - [x] ToDo 作成と lint での RM 存在チェック導入
    - メモ: `scripts/lint_todo_completion.py` に `RM-xxx` 存在検証とロードマップ照合を追加し、テストで担保。
  - [x] ブランチ命名ルールの文書化と検証手段整備
    - メモ: `AGENTS.md`／テンプレを更新し、lint で `関連ブランチ` の `prefix/rmxxx-slug` 形式を検証するように変更。
  - [x] RM 採番プロセス（RM-000 運用含む）の文書化と手順整備
    - メモ: `docs/policies/task-management.md` に RM 採番手順（RM-000→ロードマップ登録→ToDo 起票）を追記。
  - [x] ToDo 目的欄・Issue 同期時に RM を明示するルール整備
    - メモ: ToDo テンプレを RM 付き目的へ更新し、`scripts/sync_todo_to_issues.py` で Issue タイトルへ RM コードを付与。
  - [x] Mermaid 図の完了ノード扱い（削除／移動）のポリシーと自動化修正
    - メモ: `docs/roadmap/roadmap.md` を更新し、`scripts/auto_complete_todo.py` が完了ノードを削除するよう改修。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 現状確認と対応方針（全文メモ）
  - ToDo と RM の紐付けルール  
    - 現状: `docs/todo/template.md` の例示が `RM-000` のままで、`RM-xxx` が存在するかを ToDo 作成時や lint で検証する仕組みがない。結果として、ロードマップに未登録のテーマでも ToDo が作れてしまう。  
    - 対応方針: テンプレート、`AGENTS.md`、`docs/policies/task-management.md` を更新し、ToDo 作成時には既存の `RM-xxx` を必ず指定するルールを明記する。あわせて `scripts/lint_todo_completion.py` に `RM-\d{3}` 形式とロードマップ上の存在確認を追加し、違反を検知できるようにする。
  - ブランチ命名ルール  
    - 現状: ガイドラインは `feat|fix|chore|docs/<slug>` のままだが、実際のブランチは `feat/rm061-...` など `rmxxx` を含む形式で運用されており、公式記述と乖離している。  
    - 対応方針: 公式文書とテンプレートを `prefix/rmxxx-slug` 形式へ統一し、ToDo の「関連ブランチ」記入例も同じ形式にそろえる。必要であれば lint やレビューのチェック項目としてブランチ名に `rmxxx` が含まれるか検証する。
  - RM 番号を増やすプロセス  
    - 現状: ロードマップへ新しい `RM-xxx` を追加する手順が明文化されておらず、先に ToDo を作ろうとすると未登録の RM を参照することになる。口頭でロードマップを更新してから ToDo を作る運用になっている。  
    - 対応方針: `docs/policies/task-management.md` 等に、`RM-000`（ロードマップ整備用）で検討→`docs/roadmap/roadmap.md` へ `RM-xxx` 追加→該当 ToDo を `RM-xxx` で起票、という手順を明記する。ロードマップ更新と ToDo 作成を同一ブランチで行う指針も追加する。
  - ToDo 目的欄・Issue での RM 表記  
    - 現状: ToDo の目的欄に `RM-xxx` を含めるルールも、Issue タイトルへ自動反映する仕組みもないため、Issue 側から RM 番号が即座に分からない。  
    - 対応方針: ToDo テンプレの目的欄例を `RM-xxx` 付きへ改め、Issue 連携スクリプト（`scripts/sync_todo_to_issues.py` など）でタイトルに RM 番号を付与する処理を検討・実装する。
  - Mermaid 図の完了扱い  
    - 現状: `docs/roadmap/roadmap.md` では「Mermaid 図は未着手・進行中・保留のみ」としている一方、`auto_complete_todo.py` は完了したノードにも `(完了)` を付けて図に残している。文書ポリシーと自動化の挙動が一致していない。  
    - 対応方針: `auto_complete_todo.py` を修正し、完了した RM ノードを図から除外（または専用セクションへ移動）する処理へ変更する。併せてロードマップ文書も新しい扱い方に合わせて更新する。
- 次アクション候補: `docs/roadmap/roadmap.md` への RM-069 追加案作成、`docs/AGENTS.md` のブランチ／ToDo 運用ルール更新、必要に応じて `docs/policies/task-management.md` や `docs/runbooks/` の連携手順を更新する。
