# tests ディレクトリ向け作業指針

## テスト構成
- 単体テスト: ドメインごとに `tests/<domain>/` へ配置し、`src` 配下の責務と 1:1 で対応付ける。主要ディレクトリ例:
  - `tests/api/`, `tests/cli/`, `tests/template_ai/`, `tests/template_audit/`
  - `tests/prepare/`, `tests/prepare_ai/`, `tests/pipeline/<stage>/`（`analyzer` / `compose` / `content` / `mapping` / `monitoring` / `refine` / `render` / `spec_validation`）
  - `tests/layout_ai/`, `tests/layout_validation/`, `tests/review_engine/`, `tests/slide_ai/`
  - `tests/todo/`, `tests/utils/`, `tests/models/`, `tests/generate_ready/`
- 統合テスト: `tests/integration/test_cli_generate_pipeline_flow.py` が CLI から PPTX/PDF を生成するフローをカバー。サンプル JSON は `samples/` を利用。
- スクリプト検証: `tests/todo/test_todo_sync_scripts_execution.py` や `tests/cli/test_cli_template_extraction_export.py` で `scripts/` 配下の CLI ラッパーを検証。

## ディレクトリ体系とモジュール配置
- ドメイン単位で `tests/<domain>/` サブディレクトリを作成し、`src` や `docs` の責務と対応付ける。例: コンテンツ生成は `tests/content_ai/`、レイアウト関連は `tests/layout_ai/`。
- 共有ユーティリティやベースクラスのテストはフラットに残し、ドメイン横断の性質をコメントで明示する。
- サブディレクトリには必要に応じて `conftest.py` を配置し、ドメイン専用フィクスチャやモックを共通化する。

## テストファイル・ケース命名規約
- テストモジュール名は `test_<対象>_<シナリオ>.py` とし、`<対象>` をクラス名や CLI コマンド名、`<シナリオ>` を期待する挙動で記述する。
- テストクラスは `Test<対象>`、テスト関数は `test_<前提>_<期待結果>` の形式を推奨する。複数の前提条件を扱う場合はパラメータ化を優先する。
- マーカーは粒度に応じて必ず付与する。UI への副作用がない CLI 統合テストには `@pytest.mark.cli`、外部サービスモックを伴うものには `@pytest.mark.integration`、長時間実行は `@pytest.mark.slow` を利用する。

## フィクスチャとテストデータ運用
- グローバルに共有するフィクスチャはリポジトリ直下の `tests/conftest.py` に配置し、ドメイン固有のセットアップはサブディレクトリ側に切り出す。
- テキストや JSON など軽量データは `tests/fixtures/<domain>/` に配置し、読み込みヘルパー経由で再利用する。PPTX や PDF などバイナリは引き続き `samples/` を参照する。
- フィクスチャやテストデータには目的・利用条件をコメント化し、重複データの生成を避ける。

## 実行コマンド
- すべてのテスト: `uv run --extra dev pytest`
- 単一テストモジュール: `uv run --extra dev pytest tests/pipeline/render/test_renderer_rich_content.py`
- 統合テストのみ: `uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py -k "not pdf" --maxfail=1`
- PDF 変換を含むテストは LibreOffice が必要なため、実行前に `soffice --headless --version` で環境確認する。
- 差分カバレッジ確認: `uv tool run diff-cover coverage.xml --compare-branch origin/main`。`uv run --extra dev pytest` などで `coverage.xml` を生成したあと、80% 未満なら不足箇所に対するテストを追加する。
- 差分重複率確認: 上記 `diff-cover` の出力や SonarCloud の Quality Gate 通知で重複が検知された場合は、設計・実装を見直して 3% 以下になるようにする。

## 追加・更新ポリシー
- 新機能やバグフィックスでは必ず失敗パターンを先に再現させるテストを追加し、緑化を確認する。承認フローや AI レビューのテストを追加する場合は、仕様を `docs/design/design.md`・`docs/design/schema/README.md`・`docs/requirements/requirements.md` で確認する。
- 大きな生成物（PPTX/PDF）の内容確認は、ハッシュ比較や `analysis.json` のメタ情報で検証し、バイナリをリポジトリに含めない。
- テストデータを追加する場合は `samples/` に配置し、目的や前提条件をファイル冒頭にコメントとして記載する。

## レビュー時確認ポイント
- テスト名・アサーションが意図を明確に伝えているか。中間 JSON の検証では `docs/design/schema/README.md` に示されたスキーマとの差異がないかをチェックする。
- `pytest` マーカーやフィクスチャの再利用可否を確認し、重複があれば共通化を検討する。
- CI 上で実行可能なコマンドのみ使用しているか（外部サービスへの依存はモック化する）。
