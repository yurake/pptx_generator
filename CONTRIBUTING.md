# 開発ルール (CONTRIBUTING)

## 1. 開発環境
- Python 3.12 系を標準とし、仮想環境 (`uv`, `poetry`, `venv` 等) で依存を管理すること。
- .NET 8 SDK をインストールし、仕上げツール (Open XML SDK) のビルドを確認すること。
- LibreOffice をインストールし、`--headless` で PDF 変換テストが実行できる状態を維持すること。
- 共通テンプレートや設定ファイルは `templates/` `python/config/` の最新版を使用すること。

## 2. Git アイデンティティと履歴
- 著者・コミッタはグローバル設定の `user.name` / `user.email` を使用し、noreply メールは利用しない。
- 履歴を書き換えない（rebase --onto などによる著者情報の改変禁止）。
- エージェント関与を明示する場合はコミット末尾に `Co-authored-by: Codex CLI <codex@example.com>` を追記する。

## 3. ブランチとコミット
- `main` ブランチは保護対象とし、直接 push を禁止する。
- 作業ブランチは `feat|fix|chore|docs/<issue#>-<slug>` を基本とし、リリース用は `release/<major.minor>`、緊急対応は `hotfix/<tag>` を使用する。
- コミットメッセージは Conventional Commits 準拠（例: `feat(renderer): add chart support`）で、スコープは `frontend`, `backend`, `ci`, `docs`, `infra`, `deps` を主に用いる。
- 粒度の細かいコミットを積み、マージ時に Squash して履歴を簡潔に保つ。
- 必要に応じて `Co-authored-by` 行を付与し、履歴の透明性を保つ。

## 4. Pull Request 運用
- Draft PR を早期に作成し、目的・変更点・影響範囲・テスト結果・ロールバック方法を記載する。
- PR サイズは概ね 300 行以内を目安にし、超える場合は分割を検討する。
- マージ前に CI グリーン、最新 `main` への追従、コンフリクト解消を完了させる。
- 承認は最低 1 名（重要領域は CODEOWNERS などで追加）を必須とし、レビュー SLA は初回応答 1 営業日を目標とする。
- マージ方式は Squash を基本とし、必要に応じて Rebase and merge を使用する（Merge commit は禁止）。

## 5. コーディング規約
- Python: `ruff` と `black` で静的解析とフォーマットを実施、型は `mypy` で検証する。
- C#: `dotnet format` を使用し、nullable 参照型を有効にする。
- スクリプト言語 (Bash/PowerShell) は shellcheck / PSScriptAnalyzer を用いて lint する。
- コメントは必要最小限とし、ビジネスルールや非自明な処理に限定する。

## 6. 依存とバージョン管理
- Python 依存は `pyproject.toml` と `uv.lock` で管理し、追加時は `uv add` を使用する。
- .NET 依存は `dotnet add package` で追加し、`dotnet list package --vulnerable` を定期実行する。
- LibreOffice 等の外部ツールバージョンは `docs/adr/` や README に明記する。
- テンプレートファイル (.pptx/.potx) はバージョン番号付きファイル名とし、更新履歴を `docs/adr/` に追記する。

## 7. テスト方針
- 単体テスト: `python/tests/` 配下に配置し、 `pytest` を使用。JSON 入力 → PPTX 出力の検証を行う。
- 結合テスト: `tests/integration/` にサンプル JSON を用意し、パイプライン全体 (JSON→PPTX→PDF) を検証する。
- パフォーマンステスト: 30 スライド規模のケースで処理時間を計測し、結果を記録する。
- セキュリティテスト: 入力検証、脆弱性スキャン (`pip-audit`, `dotnet list package --vulnerable`) を CI で実施する。

## 8. CI/CD
- GitHub Actions で以下を実行すること。
  - Lint (`ruff`, `black --check`, `mypy`, `dotnet format`)
  - ユニットテスト (`pytest`, `.NET` テスト)
  - セキュリティスキャン (`pip-audit`, `dotnet list package --vulnerable`)
- 成果物のビルド (Docker イメージ等) はステージング環境へのデプロイ前に必ず成功させる。
- CI 失敗は最優先で修正し、`main` へのマージは常に CI Pass を条件とする。

## 9. 設定・テンプレ管理
- 変更フローと検証手順は `docs/policies/config-and-templates.md` を参照すること。
- 影響がある変更は必ず Issue / ToDo に記録し、PR レビューで合意を取る。

## 10. ドキュメント更新
- カテゴリ構成と更新ルールは `docs/README.md` に従うこと。
- 新規資料を追加する際は適切なディレクトリを選び、README の一覧を更新する。

## 11. リリース手順
- 詳細なフローは `docs/runbooks/release.md` を参照し、チェックリストに沿って進める。
- リリース後は対応状況を Slack と Release Notes で共有する。

## 12. サポート・問い合わせ
- 連絡チャネルや当番体制は `docs/runbooks/support.md` に従うこと。
- 対応ログは Issue または該当 ToDo に残し、翌営業日までに共有する。

## 13. タスク管理
- 作業を開始する前にタスクを計画したら、`docs/todo/` 配下に `YYYYMMDD-<slug>.md` 形式で ToDo リストファイルを新規作成すること。
- 雛形は `docs/todo/template.md` を利用し、必要項目を埋めて初期状態とすること。
- ファイルには目的・担当者・関連ブランチ・期限を冒頭に記載し、その下にチェックボックス形式でタスク項目を列挙すること。
- 進捗が発生したらチェックボックスを更新し、完了日時やメモを追記して履歴を残すこと。
- 作業完了後は同ファイルを PR から参照し、必要な場合は `docs/todo/archive/` へ移動して保管すること。
