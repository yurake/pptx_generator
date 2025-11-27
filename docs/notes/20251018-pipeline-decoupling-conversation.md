# stage 3-6 再設計に関する会話メモ（2025-10-18）

> **補足:** 現在は `pptx gen` が stage 5 専用コマンドとなっている。本メモは再定義前の議論記録として保存している。

## 背景整理
- ユーザーの期待: stage 3 完了後に stage 4 が実施され、stage 4 の成果物 (`generate_ready.json`) を用いて stage 5 を実行する。stage 5 の再実行では stage 4 成果物のみを参照したい。
- 既存実装: `pptx gen` が stage 3〜5を一括実行し、stage 5 が `JobSpec` を直接参照していたため、stage 4 の成果物を単独で再利用できなかった。
- ギャップ: stage 3/4の成果物が stage 5 で必要となる理由が不明瞭であり、ユーザーは stage 4 までで情報が完結する想定だった。

## 決定事項
- stage 4 と stage 5 を独立 CLI (`pptx mapping` / `pptx render`) として提供し、stage 5 は `generate_ready.json` のみを主要入力とする。
- `generate_ready.json` に `job_meta` / `job_auth` を格納し、stage 5 で `JobSpec` を再構築できるようスキーマを拡張する。
- `pptx gen` は後方互換として残しつつ、内部で `mapping` → `render` を連鎖実行する構成へ変更する。

## メモ
- 文書化タスク: README・設計/要件ドキュメントの更新、および CLI リファレンスの追補。
- 監査対応: `audit_log.json` に `generate_ready` のパスを記録し再実行トレースを確保する。
