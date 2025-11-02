# パイプライン疎結合化設計メモ（2025-10-18）

> **補足:** 現在は `pptx gen` を工程5専用コマンドとして提供しており、本メモは再定義前の検討内容を記録したものです。

## 背景
- `pptx gen` が工程3〜5（Content Approval → Mapping → Rendering/Analyzer/PDF）を一括実行しており、工程5のみの再実行や工程4成果物の再利用ができない。
- 最終像では各工程を独立 CLI として扱い、工程4の成果物（`generate_ready.json`）を工程5の唯一の入力にしたい。
- ユーザーとの冒頭議論で、工程3/4の成果物は工程4に反映済みであり、工程5には `generate_ready.json` だけを渡せる構成が望ましいと確認した。

## 目的
1. 工程4（Mapping）と工程5（Rendering/Analyzer/PDF）を分離し、個別に実行・再実行可能にする。
2. `pptx render`（仮称）が `generate_ready.json` を主入力として PPTX/分析結果/PDF を生成できるようにする。
3. `pptx gen` は後方互換を維持しつつ、新コマンドを呼び出すオーケストレーション層として再設計する。

## 変更方針
### CLI 再構成
- 追加コマンド
  - `pptx mapping`: `spec.json`・`content_approved.json`・`draft_approved.json`・`layouts.jsonl` を入力に `generate_ready.json`／`mapping_log.json` を出力。
  - `pptx render`: `generate_ready.json` を入力とし、テンプレ・ブランド設定・PDF オプションを適用して PPTX／分析／PDF を生成。
- `pptx gen` は従来フラグを受け取りつつ、内部で `mapping` → `render` を順に呼び出す。互換性のため既存引数は維持し、未指定の `content_approved` や `draft_approved` の扱いは従来どおりフォールバックする。

### データモデル
- `GenerateReadyMeta` に `job_meta` と `job_auth` を追加し、元の `JobSpec` メタ情報を保持。工程5での再構成に使用する。
- 新規ヘルパー `generate_ready_to_jobspec(GenerateReadyDocument)` を実装し、レンダリング／アナライザで必要な `JobSpec` を `generate_ready` から再構築する。
  - スライド ID は `meta.sources` 先頭要素を優先し、欠損時は `slide-{index}` を生成。
  - `elements` からタイトル／サブタイトル／ノート／本文を抽出。
  - `body`（リスト）を非アンカー箇条書き、他のリスト値をアンカー付き箇条書きとして `SlideBulletGroup` を生成（レベルは0、IDは `slide_id-<anchor>-bullet-<n>`）。
  - `headers`/`rows` を持つ辞書は `SlideTable`、`source` を持つ辞書は `SlideImage`、`type` を持つ辞書は `SlideChart`、`text` を持つ辞書は `SlideTextbox` にマッピング。

### パイプライン
- Mapping: 既存 `MappingStep` を活用しつつ、`GenerateReadyDocument.meta` に `job_meta` / `job_auth` を埋め込む。
- Rendering: `SimpleRendererStep` は従来どおり `JobSpec` を受け取りつつ、`pptx render` が事前に `generate_ready` → `JobSpec` 変換を行う。レンダリング後は `generate_ready` をアーティファクトとして保持し、監査ログの入力源に追加。
- Analyzer/PDF: 変換済み `JobSpec` を使うため従来ロジックを再利用。`generate_ready` 由来であることを監査ログに残す。

### 監査ログ
- `audit_log.json` に `generate_ready` のパスとハッシュ情報を追記し、再実行時の追跡性を確保。
- Mapping ログ・フォールバックレポートは `pptx mapping` 内で出力し、`pptx render` 実行時には既存ファイルを読み取るだけにする。

### テスト
- CLI 統合テストを再構成し、`pptx mapping` → `pptx render` の順序と `pptx render` 単体再実行シナリオを追加。
- 既存 `pptx gen` テストは後方互換保証のため更新。
- `generate_ready_to_jobspec` の単体テストを新設し、代表的な `elements` 変換と欠損時のフォールバックを検証。

## 残課題
- `docs/notes/` に冒頭会話の整理ノートを作成（ToDo で管理）。
- Analyzer が参照するアンカーやフォント情報は簡易的に生成されるため、中長期的には `GenerateReady` へ詳細メタを拡充する検討が必要。
- CLI オプションの整理（特に `--content-approved` など工程3/4向けフラグ）は段階的に deprecate 予定。今回の対応では互換性維持のみ。

## 更新記録
- 2025-10-23: `MappingStep` の `mapping_meta` に生成日時・テンプレートバージョン・フォールバック対象スライドを追加し、監査ログで `mapping_log` / `generate_ready` のハッシュ追跡を拡充。`pptx mapping` → `pptx render` 単体チェーンと `generate_ready_to_jobspec` のフォールバック経路をテスト化。
