# GitHub ラベル運用整備

## 目的
- Issue / PR のトリアージを高速化し、ToDo 自動同期や CI との連携状態を可視化する。
- ラベル命名規約を統一し、自動付与と手動運用の住み分けを明確にする。
- `github/issue-labeler` と `actions/labeler` を併用し、テンプレートや変更ファイルに応じた自動ラベルを付与する。

## ラベル分類と命名規約
| 区分 | ラベル名 | カラー例 | 用途 |
| --- | --- | --- | --- |
| 種別(Type) | `type:bug` | `d73a4a` | 不具合報告。既存 `bug` ラベルを改称して使用する。 |
|  | `type:enhancement` | `a2eeef` | 機能改善・要望。既存 `enhancement` を改称。 |
|  | `type:docs` | `0075ca` | ドキュメント整備。 |
|  | `type:task` | `fbca04` | 雑多な整備・チケット化した作業。 |
| ステータス(Status) | `status:needs-info` | `d4c5f9` | 追加情報が必要な Issue / PR。 |
|  | `status:blocked` | `b60205` | 依存タスク待ち。 |
|  | `status:ready` | `0e8a16` | レビューや実装が進められる状態。 |
| 優先度(Priority) | `priority:high` | `b60205` | 早期対応が必要。 |
|  | `priority:medium` | `fef2c0` | 通常対応。 |
|  | `priority:low` | `c5def5` | 後回し可能。 |
| 領域(Area) | `area:cli` | `c2e0c6` | Python CLI / `src/**`。 |
|  | `area:templates` | `c5def5` | `templates/**`、`samples/**`、`config/**`。 |
|  | `area:docs` | `bfdadc` | `docs/**`、`README*`。 |
|  | `area:automation` | `f8c2d7` | `.github/**`、`scripts/**`。 |
|  | `area:dotnet` | `e6e6fa` | `dotnet/**`。 |
|  | `area:llm` | `f9d5ff` | `src/pptx_generator/prepare/**`、`src/pptx_generator/prepare_ai/**`、`src/pptx_generator/slide_ai/**`、`src/pptx_generator/layout_ai/**`、`src/pptx_generator/template_ai/**`、`src/pptx_generator/pipeline/slide_alignment.py`、`src/pptx_generator/draft_recommender.py`、`config/**/*policy*.json`。 |
| 自動化 | `todo-sync` | `0e8a16` | `todo-sync` ワークフローが使用。名称を変更しない。 |
|  | `automation:ci` | `5319e7` | CI 連携確認用。必要に応じて付与。 |

### ラベル整理の手順
1. 既存 `bug` / `enhancement` ラベルを GitHub UI 上で `type:bug` / `type:enhancement` に改称し、カラーを上表に合わせる。  
2. 未使用ラベルが存在する場合はアーカイブ前に履歴を確認し、不要であれば削除する。  
3. 新規ラベルは命名規約に従い `区分:値` 形式で追加する。  
4. `todo-sync` など既存自動化が参照するラベルは名称を変更しない。必要な場合はスクリプト側の更新を別タスクで実施する。  

## 自動ラベリング設計

### Issue (`github/issue-labeler`)
- 設定ファイル: `.github/issue-labeler.yml`  
- ワークフロー: `.github/workflows/issue-labeler.yml`  
- ルール概要:
- タイトル先頭の `[Bug]` を検知して `type:bug` を付与。
- `[Feature]` を検知して `type:enhancement` を付与。
- Issue 本文に `docs/` パスや「ドキュメント」という語が含まれる場合は `area:docs` を付与。
- 「テンプレート」「branding」「generate_ready」などテンプレ関連キーワードで `area:templates` を付与。
- `.github` や `Actions`、`ワークフロー` といった語で `area:automation` を付与。
- 「LLM」「プロンプト（prompt）」「指示文（directive）」「推論設定」「モデル（model）」といった語を含む場合は `area:llm` を付与（`(?i)` プレフィックスにより英語は大小問わず一致）。
- 「Template AI」「テンプレ AI」「Layout AI」「レイアウト AI」の語句、ならびに主要 LLM プロバイダ名（OpenAI / Azure OpenAI / Anthropic / Claude / Bedrock / GPT を含む表記）も `area:llm` の対象。
  - 自動付与は精度重視で最低限とし、曖昧なケースは手動で補正する。
- `not-before` はワークフロー導入時点の日付を設定し、過去 Issue への大量付与を防ぐ。

### Pull Request (`actions/labeler`)
- 設定ファイル: `.github/labeler.yml`  
- ワークフロー: `.github/workflows/pr-labeler.yml`  
- ルール概要:
  - `docs/**`, `README*`, `docs/*.md` に変更があれば `area:docs` と `type:docs` を付与。
  - `.github/**` や `scripts/**` の変更で `area:automation` を付与。
  - `templates/**`, `samples/**`, `config/**`, `pptx/` 関連で `area:templates`。
  - `src/**`, `pyproject.toml`, `uv.lock` の変更で `area:cli`。CI で Python ロジックが主対象のため `type` 自動付与は行わず、レビュー時に判断する。
  - `dotnet/**` の変更で `area:dotnet`。
  - `src/pptx_generator/prepare/**`, `src/pptx_generator/prepare_ai/**`, `src/pptx_generator/slide_ai/**`, `src/pptx_generator/layout_ai/**`, `src/pptx_generator/template_ai/**`, `src/pptx_generator/pipeline/slide_alignment.py`, `src/pptx_generator/draft_recommender.py`, `config/**/*policy*.json`, `docs/design/cli/cli-command-reference.md`, `docs/requirements/stages/stage-01-*`, `docs/requirements/stages/stage-03-*`, `docs/design/stages/stage-01-template.md` の変更で `area:llm`。
  - 変更ファイルが 1 カテゴリに限定される場合は `type:docs` など補助ラベルを付与できるよう `all-globs-to-any-file` を活用する。
  - `!` 否定を利用し、ドキュメントのみ変更の PR には `type:docs` を付与しつつ、コード変更が混在する場合は付与しない。

### 手動補完
- 自動付与で対象外となる `status:*` や `priority:*` はトリアージ担当が手動で設定する。
- `status:needs-info` は追加質問コメントと同時に付与し、情報が揃ったら外す。
- `priority:*` はロードマップ上の位置付けに応じて設定し、ToDo 更新時に見直す。

## ワークフロー運用
- 新規ワークフローを `workflow_dispatch` でも実行できるようにし、設定変更時の検証を行う。
- 導入直後は対象 Issue / PR でラベル結果を確認し、誤付与をログ化して `docs/policies/github-label-governance.md` を更新する。
- ワークフローの変更は `docs/todo/` の対象タスクにメモしてから実装する。

## テストとリスク低減
- `github/issue-labeler` は正規表現マッチングのため、テンプレート変更に合わせて `versioned-regex` を活用する。新規テンプレートではコメント内に `issue_labeler_regex_version=<数値>` を埋め込み、設定ファイルでバージョンを切り替える。
- `actions/labeler` は構文エラーでワークフローが失敗する可能性がある。リポジトリ内で `act` を使う場合は `--job label` を利用し、`pull_request` イベントのサンプルを与えて検証する。
- ラベルの大量付け直しが必要な場合は GitHub CLI の `gh issue edit --add-label` や REST API を利用し、作業ログを `docs/notes/` に残す。

## ロールバック方針
- 自動化が問題を起こした場合は該当ワークフローを一時的に `disabled` に設定し、`docs/todo/` に対応メモを追記する。
- ラベル改称による影響が大きい場合は GitHub UI から旧ラベルへ戻し、テンプレートと設定ファイルもロールバックする。
- 影響範囲を `docs/todo/` の「テスト・検証」メモへ記録し、必要であれば `docs/runbooks/` に個別の再発防止項目を追加する。
