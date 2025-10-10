# ToDo 自動完了フロー調査メモ（2025-10-10）

## 背景
- ユーザー要望: main ブランチに「PR 作成」チェックのみ未完の ToDo が残っており、現行フローでは想定外の状態である理由を特定する。
- 対象タスク: RM-002 配下の `docs/todo/20251009-samples-expansion.md` と `docs/todo/20251009-samples-json-reorg.md` にて他チェックは完了済み。 【F:docs/todo/20251009-samples-expansion.md†L1-L22】【F:docs/todo/20251009-samples-json-reorg.md†L1-L20】

## 現状把握
- 上記 ToDo は main に存在し、PR 作成チェックのみ未完のまま。PR 番号や URL 記載もなく、自動化ワークフローが未実行と判断できる。 【F:docs/todo/20251009-samples-expansion.md†L15-L16】【F:docs/todo/20251009-samples-json-reorg.md†L15-L16】
- ロードマップ側では RM-002 が「完了」となっているが参照先が `docs/todo/` のままで、アーカイブ移動が未実施。 【F:docs/roadmap/README.md†L154-L164】

## ワークフロー調査
- `todo-auto-complete` ワークフローは PR 本文から `docs/todo/YYYYMMDD-<slug>.md` 形式のパスを grep し、検出できた場合のみスクリプトを実行する。 【F:.github/workflows/todo-auto-complete.yml†L30-L62】
- スクリプト `scripts/auto_complete_todo.py` は対象 ToDo の「PR 作成」を `[x]` に変更し、未完タスクが無ければアーカイブ移動とロードマップ更新を行う。 【F:scripts/auto_complete_todo.py†L37-L169】

## 原因仮説
1. PR テンプレートの ToDo 欄をプレースホルダーのまま残すと、grep がマッチせずワークフローがスキップされる。結果として ToDo が main に残る。テンプレートのデフォルト値 `docs/todo/<ファイル名>.md` はパターン要件を満たさない。 【F:.github/pull_request_template.md†L6-L15】【F:.github/workflows/todo-auto-complete.yml†L30-L48】
2. ワークフローは PR 本文内の ToDo パスが 1 件も無い場合に「Skip」ログを出して終了し、検知失敗をエラー化しないため気付きづらい。 【F:.github/workflows/todo-auto-complete.yml†L46-L48】
3. ToDo ファイル側に PR 情報が自動追記されていないため、手動レビューでも未完に見えてしまう。 【F:scripts/auto_complete_todo.py†L52-L69】

## 再発防止案
- PR テンプレートに入力例を追記し、占位文字列を必ず置換する旨を強調する。さらに、レビュー時に ToDo 記載を確認するチェック項目を追加する。 【F:.github/pull_request_template.md†L6-L21】
- 自動化ワークフローを拡張し、ToDo 検出結果が空だった場合は処理を失敗させる。PR 作成時にエラーとして検知できるよう、ワークフローの終了コードを非ゼロで返す。
- `todo-auto-complete` の後段に lint ステップを追加し、`docs/todo/` 配下に「完了」または「PR 作成のみ未完」の ToDo が残存していないかを走査する。完了済みフラグ（`- [x]` のみ）や PR 作成チェック以外が完了済みで `[ ] PR 作成` が残っているファイルを検出し、ワークフローをエラーで終了させる。これにより、PR 本文に対象 ToDo が書かれなかったケースでも main への取り込み前に失敗させられる。

### Lint ステップの抜け漏れ検証
- スクリプト実行後に `docs/todo/` を再帰的に読み取り、以下の条件で異常判定する。
  1. チェックボックスがすべて `[x]` で埋まっているのに `docs/todo/archive/` へ移動されていない。
  2. `- [ ] PR 作成` を除くチェックボックスが `[x]` で、PR 作成のみ未完状態が残っている。
- 1. は PR テンプレートでの記載漏れ・ワークフロー不発に加えて、`todo-auto-complete` の途中失敗や手動対応忘れでも検知可能。アーカイブ移動が完了すれば `docs/todo/` からは消えるため誤検知は生まれない。
- 2. は今回の事象そのもの。PR に対象 ToDo を書き忘れた場合でも、merge 時に lint が失敗し CI で止まる。ただし PR 作成チェックを意図的に未完とする運用（例: 承認待ちで PR 作成前に完了扱いにするケース）があると誤検知するため、運用ルール側で「PR 作成チェックは PR 作成前に完了へ倒さない」ことを明文化する必要がある。
- なお `docs/todo/` 直下以外（例: サブディレクトリ）の ToDo はテンプレート上想定していないため lint 対象から除外する。

## 次のアクション候補
- 上記再発防止案の優先順位付けと対応タスク化（`docs/todo/20251010-todo-workflow-investigation.md` を更新）。
- RM-002 関連の PR を再確認し、該当 ToDo を手動でアーカイブするか、再度 PR を作成してワークフローを実行する。 【F:docs/todo/20251010-todo-workflow-investigation.md†L1-L18】
