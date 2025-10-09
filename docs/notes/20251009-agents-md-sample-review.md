# AGENTS.md サンプル比較メモ（agents.md Web サイトより）

## 収集対象
- サイト掲載のサンプルコードブロック（基本構成の雛形）
- `openai/codex` リポジトリの AGENTS.md
- `apache/airflow` リポジトリの AGENTS.md
- `temporalio/sdk-java` リポジトリの AGENTS.md

## サンプル別の主な記載内容
- **サイト掲載サンプル**
  - `## Setup commands` で依存インストール・開発サーバー起動・テスト実行を明記。
  - `## Code style` で TypeScript 厳格モードやシングルクォート等の方針を列挙。
  - `## Dev environment tips` / `## Testing instructions` / `## PR instructions` で実行コマンドとチェック手順を具体的に提示。
  - 例:
    ```markdown
    ## Setup commands
    - Install deps: `pnpm install`
    - Start dev server: `pnpm dev`
    - Run tests: `pnpm test`
    ```
- **openai/codex**
  - サンドボックス環境変数 (`CODEX_SANDBOX_*`) や Seatbelt 実行制約の扱いを明文化。
  - Rust 向けコーディング規約（Clippy ルール、`format!` の書き方、Stylize の使い方など）を細かく記載。
  - `just` コマンドによる整形・lint・テストの順序とプロンプト確認の手順を定義。
  - スナップショットテスト更新、統合テストユーティリティ、テスト時のログ確認方法を詳述。
  - 例:
    ```markdown
    Run `just fmt` (in `codex-rs` directory) automatically after making Rust code changes; do not ask for approval to run it.
    Before finalizing a change to `codex-rs`, run `just fix -p <project>` … Additionally run the tests:
    - `cargo test -p codex-tui`
    - `cargo test --all-features`
    ```
- **apache/airflow**
  - `contributing-docs/` 配下ドキュメントへのリンクで詳細情報を参照させる構成。
  - `uv` を用いた仮想環境構築、`prek` フック導入、Breeze（Docker テスト環境）の活用手順をまとめている。
  - ドキュメントビルド方法、PR ガイドライン、上級者向け資料へのリンクも網羅。
  - 例:
    ```markdown
    - Install with `uv tool install prek` and run checks via `prek --all-files`.
    - Use Breeze for integration tests: `breeze --backend postgres --python 3.10 testing tests --test-type All`.
    - Build docs locally: `uv run --group docs build-docs` / `breeze build-docs`.
    ```
- **temporalio/sdk-java**
  - リポジトリレイアウト（主要ディレクトリの役割）を先頭で説明。
  - `./gradlew` 系コマンドによるフォーマット・テスト・ビルド方法を列挙し、パッケージ別テストの指定方法を記載。
  - コミットメッセージ規約（Chris Beams 準拠）や PR で回答すべき観点を明記。
  - レビュー時チェックリスト（spotless、テスト、ドキュメント更新）で完了条件を定義。
  - 例:
    ```markdown
    Format before committing: `./gradlew --offline spotlessApply`
    Run core tests: `./gradlew :temporal-sdk:test --offline --tests "io.temporal.workflow.*"`
    Build all modules: `./gradlew clean build`
    ```

## カテゴリ別に見られた必須要素
- **開発環境セットアップ**: 言語/ランタイムのバージョン、仮想環境作成コマンド、Docker/Breeze など代替環境の説明。
- **依存ツール・コマンド**: Lint・フォーマッタ（`just`, `spotless`, `prek`）、ビルドスクリプト、補助 CLI の導入方法。
- **テスト戦略**: 単体・統合・スナップショットの実行手順と、どの範囲まで必須かの明文化。
- **コードスタイル / 実装規約**: 言語固有のルール、推奨スタイル、禁止事項、ファイル局所の慣例まで掘り下げる例が多い。
- **リポジトリ探索ガイド**: ディレクトリ構成や関連ドキュメントの配置を説明し、詳細は各 doc へ誘導。
- **コミット・PR 運用**: メッセージ形式、レビューで確認すべき観点、テスト・lint 必須条件。
- **環境制約・安全運用**: サンドボックスで動かない処理、外部ツール利用時の注意、承認が必要なコマンドなど。
- **高度なトピック**: スナップショット更新、ドキュメントビルド、API バージョニング、フォールバック手順などの補足。

## pptx_generator での適用検討
- 既存 AGENTS.md ではセットアップ・テスト・スタイル・タスク管理を整理済みだが、以下の追加余地がある:
  - `tests/` 階層別の目的やサンプル（例: CLI 統合テスト vs レンダラー単体テスト）の使い分け。
  - `docs/` 配下ドキュメントの参照ガイド（設計・ポリシー・ロードマップなどへの動線）。
  - サンドボックス/外部ツールの制約（LibreOffice や .NET ツールの実行条件、PDF 変換環境）。
  - PR レビュー観点や完了チェック（テストレポート更新、テンプレート差分確認等）の具体化。
  - セキュリティ・データ取り扱い上の注意点（ブランド JSON／案件情報の扱い）を整理するセクション。
- 上記を反映することで、エージェントが必要情報を AGENTS.md のみで把握できる状態に近づけられる。
