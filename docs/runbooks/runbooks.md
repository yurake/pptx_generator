# Runbook 索引

## 目的
- `docs/runbooks/` にある運用手順書の役割と利用タイミングを整理する。
- 対応内容に応じて必要な runbook を素早く特定できるよう、前提や補助資料への導線をまとめる。

## 参照手順
1. 実施したい手順と対象範囲を明確にし、以下の表から該当 runbook を選ぶ。
2. 関連するポリシー（例: `docs/policies/task-management.md`, `docs/policies/config-and-templates.md`）を確認し、前提条件や更新フローと矛盾しないかチェックする。
3. 作業後は ToDo やロードマップへ結果を記録し、runbook に追記が必要なら本ファイルと併せて更新する。

## Runbook 一覧

| ファイル | 主な用途 | 補助資料 |
| --- | --- | --- |
| `release.md` | テンプレ／CLI のリリース手順とロールバック。環境メタの記録や静的テンプレ外部フックの依存同期・テーブルマッピング整合チェックを含む。 | `docs/policies/task-management.md`, `docs/policies/config-and-templates.md` |
| `support.md` | 問い合わせ対応や障害時の一次対応フロー。連絡先・ログ採取手順・恒久対応メモの残し方を定義。 | `docs/policies/task-management.md`, `docs/notes/*` |
| `story-outline-ops.md` | ストーリー骨子の運用と承認プロセス。差戻しや巻き戻しの手順を含む。 | `docs/design/stages/stage-03-compose.md`, `docs/policies/context-engineering.md` |
| `pptx-analyzer.md` | Analyzer を使ったレンダリング確認と監査ログ分析。`analysis.json` や `mapping_log.json` の読み解き方法を説明。 | `docs/design/architecture/cli-command-reference.md`, `docs/policies/config-and-templates.md` |

## 更新時チェック
- 新しい runbook を追加したら本索引と `docs/README.md` を更新する。
- 既存 runbook の構成や前提が変わった場合は、関連ポリシー・設計ドキュメントとの整合を確認する。
- ToDo やノートに作業履歴を残し、runbook で発見した改善事項を次回タスクへ引き継ぐ。
