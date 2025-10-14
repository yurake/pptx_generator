# スキーマ概要

## 目的
- PPTX 生成パイプライン全体で利用する JSON 仕様を整理し、工程間で一貫性を保つ。
- 入力仕様の拡張と中間データの標準化を通じて、HITL 承認・マッピング・レンダリングを連携させる。
- スキーマ変更が実装（`models.py`）やテストに与える影響を明示する。

## 入力仕様の拡張（2025-10-05）
- `slides[].tables`: 列ヘッダ `columns`、行データ `rows`、装飾 `style.header_fill`, `style.zebra` を定義。
- `slides[].charts`: `type`, `categories`, `series[].{name, values, color_hex}`, `options.data_labels`, `options.y_axis_format` を追加。
- カラーフィールドは `#` の有無を正規化し、既存 `FontSpec` と同じスタイルを適用する。

### 実装メモ
- `src/pptx_generator/models.py` にテーブル・チャート用モデルを追加し、`pydantic` バリデーションを実装。
- サンプル仕様（`samples/json/sample_spec.json`）にテーブル／グラフの例を追加する。
- `tests/test_models.py` でフィールド読み込みとデフォルト値を検証する。

## 中間 JSON の整理（2025-10-11）
- 工程 3〜6 で扱う `content_*`, `draft_*`, `rendering_ready.json`, `mapping_log.json`, `rendering_log.json`, `audit_log.json` を工程別に定義。
- 詳細は `content.md`, `draft.md`, `mapping.md`, `rendering.md` に記載し、サンプルを `samples/` に配置する。

## 今後のタスク
- 承認 UX 仕様 (`docs/policies/task-management.md`) とスキーマの整合を定期確認する。
- スキーマ検証 CLI の導入（`uv run tools/schema check <file>` 仮）を検討する。
- LLM 連携で追加されるメタ情報（トレース ID など）をスキーマに取り込むか判断する。
