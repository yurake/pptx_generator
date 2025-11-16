# docs ディレクトリ向け作業指針

## 目的
- `docs/` 配下の資料構造と更新ルールを統一し、エージェントが適切な場所にドキュメントを追加できるようにする。

## 作業前チェック
- ToDo 運用ルールは `docs/todo/README.md` に集約している。Plan 承認後に対象作業へ着手する際、紐づく ToDo を確認し、必要に応じて作成・更新する。コードに影響しない整備タスクでユーザーが ToDo 不要と明示した場合のみ省略できる。不明なときは必ずユーザーへ相談する。
- 追加・更新する資料のカテゴリが `docs/README.md` に定義されているかを確認する。
- 既存資料に関連する ADR やポリシーがある場合は先に参照し、整合性の取れた更新内容にする。
- 作業開始前に Plan を提示し承認を得る。承認方針は `docs/policies/task-management.md` の「Approval-First Development Policy」を参照。
- 生成フローや承認ステップに関する仕様は `docs/notes/20251011-roadmap-refresh.md` と `docs/design/design.md` を起点に確認し、実装・要件ドキュメント側で詳細を更新する。`docs/AGENTS.md` には概要のみを残し、重複記述を避ける。

## ToDo 運用との連携
- テンプレートを `docs/todo/template.md` からコピーする際は各チェック項目に付いた注意書きを削除しない（例: 「PR 作成は todo-auto-complete が自動更新するため手動でチェックしない」）。手動更新禁止の工程を維持したまま、必要なメモのみ追記し、チェック完了時に初めて注意書きを実績メモへ差し替える。
- ToDo 作成手順・更新ルール・アーカイブ方法は `docs/todo/README.md` に記載している。`docs/` 配下の作業では同ガイドを常に参照し、進捗ログを一元管理する。
- ToDo を省略する条件やフローは `docs/policies/task-management.md` で定義されている。最新ルールに沿って運用し、判断に迷う場合はユーザーへ確認する。

## カテゴリと配置ルール
- `README.md`: リポジトリの入口。環境セットアップ、主要 CLI のクイックスタート（`tpl-extract`, `tpl-release`, `gen` など）の使い方と出力例を掲載し、詳細仕様は専門ドキュメントへリンクする。
- `docs/policies/`: 運用ルール・手順。設定変更やタスク運用のような規約レベルの改訂はここにまとめ、README の一覧も更新する。
- `docs/requirements/`: ビジネス要件や期待機能。スキーマ変更など仕様に関わる内容を追加する。
- `docs/design/`: アーキテクチャ・実装方針。図表や構成案を含める場合は、関連箇所からリンクする。
  - `docs/runbooks/`: リリース・サポートなどの実務手順。チェックリストを更新した場合は該当 ToDo にメモを残す。ストーリー骨子運用は `docs/runbooks/story-outline-ops.md` に手順を追記し、工程3/4 ドキュメントと整合させる。Polisher / PDF 連携やレンダリング監査ログ（`rendering_log.json` / `audit_log.json`）のトラブルシューティングは `docs/runbooks/support.md` に集約し、CLI オプションの変更と同期する。Analyzer 連携の運用手順は `docs/runbooks/pptx-analyzer.md` を参照し、`mapping_log.json` の Analyzer サマリ確認も実施する。
- `docs/notes/`: 調査メモや議事録。短期的な共有事項はここに保存し、アーカイブ化が必要なら `docs/todo/` のメモにも記録する。
- `docs/roadmap/`: 大項目 ToDo。テーマステータスを更新した場合は、関連する ToDo ファイルから相互リンクを張る。
- `docs/todo/`: ToDo 管理。テンプレートに沿った更新ルールは `docs/todo/README.md` を参照。
- `config/`: 章テンプレ辞書（`config/chapter_templates/`）や差戻し理由テンプレ（`config/return_reasons.json`）など、CLI で参照する設定を配置。更新時は対応する requirements/design/runbook へ根拠を記録する。
  - `config/usage_tags.json` を改訂する場合は Template AI / layout AI の語彙整合を確認し、`docs/requirements/stages/stage-01-template-pipeline.md` と `docs/design/stages/stage-01-template-pipeline.md` の記述を更新する。環境変数で `mock` 以外を利用する手順を README と runbook に反映すること。
- `assets/`: ロゴ・図版など共有資産の保管場所。更新フローと注意事項は `assets/README.md` を参照し、機微情報が混入していないかを必ず確認する。

## 更新手順
1. 追加・改訂する資料のカテゴリを決め、該当ディレクトリに Markdown ファイルを作成・編集する。
2. カテゴリの README（例: `docs/README.md`, `docs/roadmap/roadmap.md`）を更新し、新規資料へのリンクを追記する。
3. フロー・承認・AI レビューなど仕様面の変更は、必ず `docs/design/design.md`・`docs/design/layout-style-governance.md`・`docs/design/schema/README.md`・`docs/requirements/requirements.md` などの専門ドキュメントにも反映する。`docs/notes/20251011-docs-update-plan.md` を参照し、対象範囲を確認する。
4. 変更内容を ToDo のメモに反映し、必要に応じてロードマップや関連ドキュメントへリンクを追加する。
5. コミット前に `git status` で対象ファイルを確認し、不要な差分（バイナリやキャッシュ）が混入していないかをチェックする。

## レビュー時の確認ポイント
- `docs/README.md` のカテゴリ一覧に抜け漏れがないか。
- 関連するポリシー・要件・デザイン文書が最新の前提で書かれているか。
- 作業ログ（ToDo、ノート、ロードマップ）が更新され、追跡可能な状態になっているか。
