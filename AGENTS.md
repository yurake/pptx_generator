# 1 基本原則
- 言語は日本語で統一
- コメントで過去の変更に言及しない

# 2 ポリシーと記録
- 開発手順は `CONTRIBUTING.md` を参照する
- 実施したことや検討した内容は `docs/` に記録する

# 3 開発環境セットアップ
- Python 3.12 系の仮想環境を用意し、`uv sync` で依存を同期する。
- .NET 8 SDK と LibreOffice (headless 実行可能) をインストールし、Open XML SDK ベースの仕上げツールと PDF 変換が動作することを確認する。
- `uv` コマンドが利用できない場合は <https://docs.astral.sh/uv/getting-started/installation/> を参照し導入する。

## セットアップコマンド
- 依存同期: `uv sync`
- CLI 実行準備: `uv run --help` でエントリーポイントが認識されているか確認する
- PDF 変換確認 (任意): `soffice --headless --version`

# 4 CLI 実行の基本
- 入力 JSON を `samples/sample_spec.json` から派生させ、必要に応じてブランド設定 JSON (`config/branding.json`) やテンプレート (`templates/*.pptx`) を指定する。
- PPTX と解析結果を生成する基本コマンド:
  ```bash
  uv run pptx-generator run samples/sample_spec.json
  ```
  - 出力先は既定で `.pptxgen/outputs/`。`--workdir` で変更可能。
  - ブランド設定を差し替える場合は `--branding <path>` を指定する。
  - `--export-pdf` で LibreOffice 経由の PDF 生成を有効化できる。

# 5 テスト・検証
- 単体・統合テストを含む全体テスト:
  ```bash
  uv run --extra dev pytest
  ```
- CLI 統合テストのみを実施する場合:
  ```bash
  uv run --extra dev pytest tests/test_cli_integration.py
  ```
- テスト実行後は出力ディレクトリ (例: `.pptxgen/outputs/`) を確認し、期待する PPTX / PDF が生成されているか確認する。
- テスト階層やケース追加の方針は `tests/AGENTS.md` を参照する。統合テストでは `samples/` のデータを活用し、バイナリ差分はハッシュやメタ情報で検証する。

# 6 コードスタイルと静的解析
- Python: `ruff`, `black --check`, `mypy` を利用する。未導入の場合は `uv tool install <package>` で単体インストールしてから以下を実行する。
  ```bash
  uv tool run --package ruff ruff check .
  uv tool run --package black black --check .
  uv tool run --package mypy mypy src
  ```
- C#: `dotnet format` を実行し、Open XML SDK を含むプロジェクトでフォーマット崩れがないか確認する。
- シェルスクリプトが対象の場合は `shellcheck` を使用する。

# 7 タスク管理とドキュメント更新
- 作業開始前に `docs/todo/` に `YYYYMMDD-<slug>.md` 形式で ToDo を作成し、進捗状況を適宜更新する。テンプレートは `docs/todo/template.md`。
- 大項目やロードマップ更新が必要な場合は `docs/roadmap/README.md` も併せて調整する。
- 調査結果や検討事項は `docs/` 配下の適切なカテゴリ (例: `notes/`, `policies/`, `runbooks/`) に記録する。
- ドキュメントカテゴリと更新手順の詳細は `docs/AGENTS.md` を参照。追加資料を作成した際はカテゴリ README を更新し、ToDo にメモを残す。

# 8 コミット・PR 運用
- コミットメッセージは Conventional Commits (`type(scope): subject`) に従う。例: `docs: update agents guidance`
- 変更は粒度の細かいコミットに分割し、意図が追跡しやすい履歴を残す。
- 作業ブランチは `feat|fix|chore|docs/<slug>` などを使用し、`main` への直接 push は禁止。
- PR はテンプレートに沿って作成し、目的・影響範囲・テスト結果・ロールバック手順を必ず明記する。
- マージ前に CI 緑化、最新 `main` への追従、コンフリクト解消を完了させる。
- PR 説明では「変更内容」「背景」「破壊的変更の有無」「関連 ToDo / ドキュメント」を明示し、レビュー観点に応じて `tests/AGENTS.md` や `docs/AGENTS.md` のガイドに沿った更新を確認する。
- 事前承認で得たユーザーのメッセージリンクまたは ID を PR 説明と必要なコミット本文に記録する。

# 9 設定・テンプレートの注意点
- テンプレートとして使用できるのは `.pptx` のみ。`.potx` を使う場合は PowerPoint で `.pptx` に書き出す。
- JSON 仕様の `layout` はテンプレートのレイアウト名と一致させる。アンカー指定が必要な図形にはユニークな名前を設定し、JSON の `anchor` に同名を記述する。
- 配色・フォントは `config/branding.json` を参照して適用されるため、テンプレート側で変更しても自動反映されない点に注意する。
- 設定やテンプレートを更新した際は、理由と影響範囲を ToDo および関連ドキュメント (`docs/policies/config-and-templates.md` 等) に記録する。

# 10 サブディレクトリ専用ガイド
- `docs/`: ドキュメントカテゴリと更新手順は `docs/AGENTS.md` を参照。
- `src/`: コード構成とテスト方針は `src/AGENTS.md` を参照。
- `tests/`: テストケースの追加規則は `tests/AGENTS.md` を参照。
- `scripts/`: GitHub 連携スクリプトの実行条件は `scripts/AGENTS.md` を参照。
- `samples/`: サンプルデータの更新ルールは `samples/AGENTS.md` を参照。
- `config/`: ブランド・ルール設定の変更手順は `config/AGENTS.md` を参照。
- 他ディレクトリに専用の AGENTS.md を追加した場合は、このリストを更新してリンクを追記する。

# 11 データ・セキュリティと外部ツール
- 案件固有のデータやブランド設定 JSON には機微情報が含まれるため、公開リポジトリへコミットしない。サンプル化が必要な場合は匿名化して `samples/` へ配置する。
- LibreOffice や .NET など外部ツールのバージョン差異で動作が変わる場合は `docs/policies/config-and-templates.md` に追記し、必要なら `docs/runbooks/` にフォールバック手順を記録する。
- 追加で API キーや認証情報が必要な処理は、必ず環境変数経由で読み込み、ドキュメントに必要な前提条件を明記する。

# 12 Approval-First Development Policy
- すべての開発作業は実装前に計画（Plan）をまとめ、ユーザーの明示的な承認を得てから着手する。承認前にコード・設定・ドキュメントを変更しない。
- Plan には scope、影響ファイル、リスクや前提、テスト戦略（単体／統合）、ロールバック方法を箇条書きで含める。緊急対応時も最小限の Plan を提示し、承認を待つ。
- 承認を得たメッセージ ID やリンクを PR 説明およびコミット本文に記録する。Plan の内容を変更する際は作業を中断し、更新版 Plan への再承認を得る。
- 詳細な運用手順とチェック項目は `docs/policies/task-management.md` の「Approval-First Development Policy」を参照する。
