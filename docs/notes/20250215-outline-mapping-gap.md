# 工程4/工程5 の CLI 入力仕様ギャップ調査（2025-02-15）

## 背景
- README.md を更新する過程で、CLI チートシートの工程4→工程5 の接続を明示しようとしたところ、`pptx mapping` が工程4の成果物 (`draft_approved.json`) をそのまま参照できないことが判明した。
- 現状の CLI 実装では、工程5 (`pptx mapping`) が内部で工程4の処理を再実行しており、工程4で手動調整した結果を確実に引き継げない。
- 仕様と README の整合をとるため、原因と影響範囲を整理する。

## 確認内容

### CLI 実装の挙動
- `src/pptx_generator/cli.py:1540` 付近の `mapping` コマンド実装を確認。
  - `mapping` は `spec_path`（工程0/3で使用する jobspec）、`--content-approved`、`--draft-output` などを受け取り、`_run_mapping_pipeline` を呼び出す。
  - `_run_mapping_pipeline` 内で `ContentApprovalStep` → `DraftStructuringStep` → `MappingStep` を順に実行しており、工程4の処理（ドラフト構成）を再度実行する構造になっている。
  - `--draft-output` で指定したディレクトリに `draft_draft.json` / `draft_approved.json` を再生成して上書きする。
  - `--layouts` を指定しない場合はスコアを既定値で補う（ログメッセージで確認）。
- `DraftStructuringStep`（`src/pptx_generator/pipeline/draft_structuring.py`）は `content_approved` と `layouts.jsonl` を前提にドラフトを再構築する。既存の `draft_approved.json` を直接読み直すロジックはない。
- `MappingStep` 側も `draft_approved.json` を入力として受け取る API は用意されておらず、`PipelineContext` 上の `draft_document` アーティファクトを参照する。

### README との不整合
- README では工程4の CLI (`pptx outline`) で承認済みドラフトを出力できると説明している。
- しかし工程5の CLI (`pptx mapping`) は工程4の成果物を直接参照しないため、README 上で「工程4出力を工程5が入力として用いる」と記載すると実装と矛盾する。
- 現在の README 更新では、工程5 の説明に「`.pptx/draft/draft_approved.json` を再生成しつつレイアウト割り付け」と明示し、工程4成果物が入力として使われない点を補足した。

### ユーザー影響
- 工程4で手動編集（HITL）したドラフトを `.pptx/draft/` に保存しても、`pptx mapping` 実行時に上書きされるため、変更が反映されない。
- README や他ドキュメントで工程4の手順を案内する際、工程5へ進む前に手動編集結果を保持する方法が存在しないことに注意が必要。
- API 側（DraftStore 等）ではドラフトを保持する仕組みがあるが、CLI 経由では再利用できない。

## 課題と提案
- CLI 仕様改善案
  1. `pptx mapping` に既存ドラフト (`draft_approved.json`) を明示的に入力できるオプションを追加する。
     - 例: `--draft-approved path/to/draft_approved.json` を指定した場合は `DraftStructuringStep` をスキップし、既存ファイルを読み込む。
     - 既存の `--draft-output` とバッティングしないよう、入力専用オプションを新設する。
  2. `pptx mapping` 内部で `draft_output` ディレクトリに既存ファイルがある場合は警告を表示し、上書き前にバックアップする。
     - 少なくとも README に「再生成される」旨を明示し、HITL で編集したファイルを避難する手順を提案する。
- ドキュメント対応
  - README の工程説明に「工程5 実行時に `.pptx/draft/` は上書きされる」旨を記載済み。より詳しい運用フローは `docs/design/cli-command-reference.md` や工程別ガイドへの追記を検討する。
  - `docs/requirements/stages/stage-04-mapping.md` にも仕様ギャップを明記し、将来の改善策を TODO として記録すると良い。

## 次のアクション（案）
1. CLI 側で既存ドラフトを入力できるオプション追加のタスクを起票（要 ToDo / Issue）。
2. 工程5 のドキュメント（requirements / design）に現状仕様を追記。
3. README の CLI チートシートに補足（「既存ドラフトは再生成される」旨）を継続掲載。

調査メモは以上。改善の優先度はユーザーのドラフト編集フローに依存するため、ロードマップの検討が必要。
