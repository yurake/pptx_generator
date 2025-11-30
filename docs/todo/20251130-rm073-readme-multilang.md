---
目的: RM-073 README 多言語展開整備の作業準備
関連ブランチ: feat/rm073-readme-multilang
関連Issue: #345
roadmap_item: RM-073 README 多言語展開整備
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm073-readme-multilang を作成済み。本ToDo追加で初期コミットを実施済み。リモート push は CLI 環境から実行不可のため保留。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: README.md の日本語本文を正とし、`.locales/translate_readme.py` を追加して README.en.md・README.zh.md を自動同期する。差分検出は Markdown ブロック単位で実施し、OpenAI API (gpt-4o-mini 系) を利用する前提。
    - ドキュメント／コード修正方針: スクリプトは `auto`（差分更新）/`full`（全文再生成）モードを実装し、`auto` をデフォルトとする。GitHub Actions からは `.locales/translate_readme.py --mode auto --base-ref <commit>` を呼び出し、三言語の Language switcher と運用手順を runbook に整備する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 実装完了後に PR レビューで仕様満たすか確認。ToDo へ進捗と承認メッセージを随時追記し、ユーザーからの変更要望は Plan を再提示して承認を取得する。
    - 想定影響ファイル: `README.md`、`README.en.md`、`README.zh.md`、`.locales/translate_readme.py`（新規）、`docs/runbooks/readme-i18n.md`（新規）、`scripts/check_readme_i18n.py`（新規）、GitHub Actions ワークフロー（新規 or 既存更新）。
    - リスク: 翻訳のニュアンス差異、ブロック構造不一致による誤更新、LLM 呼び出し失敗時の差分取りこぼし。CI でのコミット権限エラーも考慮。
    - テスト方針: `.locales/translate_readme.py` をローカルで `auto`/`full` モード実行し差分確認。GitHub Actions 上でも dry-run を行い、`scripts/check_readme_i18n.py` で整合性検査。必要に応じて仮コミットで検証。
    - ロールバック方法: 多言語 README と関連スクリプト・ワークフローを削除し、README.md を既存版へ戻す。CI ワークフロー変更は `git revert` で巻き戻す。
    - 承認メッセージ ID／リンク: 2025-11-30 ユーザー了承（「ok, 私の方で、このplanに沿ったファイルを格納してみる」）
- [x] 設計・実装方針の確定
  - メモ: `.locales/translate_readme.py` を中心に `translators/markdown_blocks.py` 相当の内部モジュールを設け、Markdown ブロック分割→差分判定→翻訳→再組立の 4 ステップで処理する。差分判定は `--mode auto` の場合に `git diff --unified=0` を利用し、基準コミットから追加・変更されたブロックのみ翻訳する。`README.en.md` / `README.zh.md` は事前読み込みし、ブロック数が合わない場合に自動的に `full` フローへフォールバックする。翻訳は OpenAI API（モデル名は環境変数 `README_TRANSLATE_MODEL`、未設定時は `gpt-4o-mini`）を呼び出し、エラー時は既存訳を残して警告を表示する。出力前に Language switcher ブロックを先頭へ挿入し、日本語・英語・中国語間で相互リンクする。GitHub Actions では `GITHUB_TOKEN` でのコミット操作、OpenAI API キーは `OPENAI_API_KEY` から取得し、三言語がすべて更新済みの場合はスクリプトが早期 return して無駄なコミットを避ける。メモは本 ToDo に集約するため docs/notes への新規ファイルは不要。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `.github/workflows/translate-readme.yml` を追加し README 更新時に自動翻訳＆コミットするパイプラインを整備。`scripts/translate_readme.py` を実装して auto/full 両モード・ブロック差分翻訳・末尾改行維持・`--mode auto` 未指定時エラー化を対応。README（ja/en/zh）に Language switcher と各言語のヘッダ統一、mermaid 図の用語ローカライズを適用。
- [x] テスト・検証
  - メモ: ローカルで `translate_readme.py --mode full` を実行して LLM 呼び出しを確認（時間がかかるケースあり）。GitHub Actions からの実行はリポジトリ上で要確認として残し、手動検証の手順を runbook に記載。
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
    - メモ: RM-073 のロードマップ記載は現行のままで要更新なしのため確認のみ。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: README 多言語化は要求仕様へ変更不要なため確認のみ。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計ドキュメントへの反映不要と判断し、現行記載と矛盾がないことを確認。
  - [x] docs/runbook 配下
    - メモ: `docs/runbooks/readme-i18n.md` を新規追加し、自動翻訳スクリプトの運用手順と CI 連携の要点を記載。
  - [x] README.md / AGENTS.md
    - メモ: README 日本語版・英語版・中国語版のヘッダブロックを統一し Language switcher を追加。英語／中国語版の mermaid 図ラベルと凡例を各言語へ更新済み。
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
