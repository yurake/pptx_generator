# src ディレクトリ向け作業指針

## 構成概要
- エントリーポイント: `pptx_generator/cli.py`（`pyproject.toml` の `pptx` スクリプト）。
- ドメインモデル: `pptx_generator/models.py` で JSON スキーマを定義。変更時は `tests/test_models.py` と `samples/` を更新する。
- パイプライン: `pptx_generator/pipeline/` 配下に Analyzer・Renderer・Refiner・PDF Exporter などのステップが分割配置されている。責務を跨ぐ変更は `docs/design/overview.md` のイントロ図と整合性を保つ。承認フローや中間 JSON (`content_approved.json`, `draft_approved.json`, `rendering_ready.json`) の仕様は `docs/design/schema-extensions.md` を参照する。

## コーディングルール（Python）
- 型ヒント必須。`mypy` でエラーが出ないことを確認する。
- 例外メッセージはユーザー操作に結びつけて記述し、ログ拡張が必要なら `pipeline/base.py` の抽象層を利用する。
- 新規ファイル追加時は `__all__` と `__init__.py` の公開設定を見直し、不要な import 循環を防ぐ。

## 実装時の動作確認
- 単体テスト: 対象モジュールに応じて `pytest` のマーカーを絞る。例: `uv run --extra dev pytest tests/test_renderer.py`。
- パイプライン全体: `uv run pptx gen samples/json/sample_spec.json --workdir .pptxgen` を実行し、`outputs/audit_log.json` の差分を確認。
- PDF 変換: LibreOffice がインストールされている環境で `--export-pdf` と `--pdf-mode=only` の双方を確認する。

## 変更とドキュメントの同期
- パイプラインの挙動が変わる場合は `docs/design/overview.md` および関連する runbook を更新する。HITL / AI レビューの変更時には `docs/requirements/overview.md` と `docs/policies/task-management.md` との整合も確認する。
- CLI インターフェース変更時は `README.md` の利用例と `samples/` の JSON を最新化する。
- ブランド／ルール設定 (`config/*.json`) に依存する変更は `docs/policies/config-and-templates.md` に追記する。

## レビュー時確認ポイント
- 影響範囲のテスト（単体 + CLI 統合）が追加・更新されているか。
- `analysis.json`, `audit_log.json` 等の生成物仕様が変わる場合、その記載が `docs/` と一致しているか。
- 例外やログのメッセージがユーザーにとって理解しやすく、サンドボックス環境でも再現確認が可能か。
