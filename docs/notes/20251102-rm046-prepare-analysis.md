# RM-046 生成AIプレペア構成自動化 初期調査（2025-11-02）

## 背景
- ロードマップ `RM-046 生成AIプレペア構成自動化` の実装前調査として、現行の stage 3（コンテンツ準備）仕様と CLI 実装を確認。
- 既存仕様はテンプレート構造を前提とした `JobSpec.slides` を AI 入力に用いており、ロードマップが求める「テンプレ依存を排した抽象プレペア出力」と乖離している。

## 現行フロー整理（旧仕様の確認）
- 当時の `docs/requirements/stages/stage-02-prepare.md` は従来のコンテンツ承認 JSON（テンプレ由来の `slide_id` / `intent` を維持）を前提に記載されていた（現在は PrepareCard ベースへ更新済み）。
- `src/pptx_generator/cli.py` の `pptx prepare` コマンド（旧実装）は `SlideAIOrchestrator` が `JobSpec.slides` から `ContentSlide` を生成し、`content_draft.json` を出力していた。
- `SlideAIOrchestrator`（当時の `src/pptx_generator/slide_ai/orchestrator.py` 59-146 行）は各スライドのレイアウト名をプロンプト解決に使用し、レイアウトごとの `intent` をポリシーから取得していた。
- `docs/design/schema/stage-02-prepare.md` も `elements.title/body` をレイアウトと 1:1 で結び付けるスキーマを想定しており、プレペア抽象化は考慮されていなかった。

## ギャップと課題
- **テンプレ依存**: 現行は `layout` と `anchor` を前提としたスライド ID を保持し、テンプレ変更に引きずられる。RM-046 では章／メッセージ単位の抽象カードへ再設計する必要がある。
- **入力形態**: `pptx prepare` が常に `spec.json` を必須とするため、生情報（案件プレペア、取材メモ等）を直接流し込むフローを想定できない。
- **出力構造**: `ContentSlide.elements.body` の 40 文字×6 行制約はテンプレ向けに最適化されており、章骨子・メッセージ・支援コンテンツなど複数粒度を保持できない（その後 RM-068 で制約を撤廃済み）。
- **HITL ログ**: `content_review_log.json` はスライド ID ベースであり、抽象カード同士の結合／バージョン履歴を保持できる構造になっていない。
- **後 stage 整合**: 旧 stage 4（当時の `docs/requirements/stages/stage-03-compose.md` 53 行付近）が legacy コンテンツ承認 JSON のストーリー情報を参照する設計になっており、抽象カード化に合わせたプロパティ再定義が必要。

## 方向性メモ
- `pptx prepare` を「プレペアビルダー」モードへ再定義し、テンプレ非依存の入力（`--prepare-source` など）を受け付ける案。ポリシーは既定値固定で扱う。
- 新しい `PrepareCard` モデルは `role.story_phase` / `role.intent_tags` と `content.title` / `content.headline` / `content.body[]` / `content.notes[]` を中核に据え、テンプレート依存要素（layout, status, supporting_points 等）を排除して抽象カードとして定義する。
- HITL ログは `card_id` と `version`（ETag 相当）を持たせ、差戻し・再生成履歴を保持。AI 生成ログもカード単位で参照できるよう `ai_generation_meta.json` を再設計する。
- 後 stage に引き継ぐため、章 → セクション → カードの階層構造と `layout_hint` へ渡すためのメタ情報（優先レイアウトカテゴリ、情報密度指標など）を定義する必要がある。既存のドラフト構成処理は PrepareCard を受け取る前提に更新済みのため、RM-046 では Stage3 出力の体裁を整えることに集中できる。
- スキーマ更新時は `docs/design/schema/stage-02-prepare.md` と `docs/requirements/stages/stage-02-prepare.md` を同時更新し、`samples/` 配下に PrepareCard 前提のサンプル（例: `samples/prepare/prepare_card.sample.jsonc`）を追加する。

## CLI インターフェース検討
- 要望: `uv run pptx prepare <prepare file>` でプレペア入力を直接指定し、従来必須だった `spec.json` 引数を不要化する。
- 影響:
  - `src/pptx_generator/cli.py` の `content` コマンド定義（~1040-1260 行）でポジショナル引数 `spec_path` を廃止し、新たに `prepare_path`（必須）を受け取る設計へ変更。
  - Spec 情報が必要な処理（例: `ContentApprovalStep` で既存 spec を適用する分岐）は既存実装側に委譲する前提で整理。従来の `--content-approved` / `--content-review-log` は Prepare モードでは使用不可と明記する。
  - `ContentImportService` を経由した複数ソース取り込みは `prepare_path` の拡張（JSON で複数参照を列挙する等）として別途検討する。
- TODO: コマンドリファレンス（README, docs/runbooks/, docs/requirements/stages/stage-02-prepare.md）で新シグネチャを反映し、サンプルコマンドを更新する。

## ContentSlide の扱い整理
- 依存箇所:
  - stage 3: `PrepareAIOrchestrator`, `PrepareNormalizationStep`, API ストア（`PrepareStore`）が `PrepareCard` を前提に動作。
  - stage 4: `DraftStructuringStep` が `ContentSlide` の `intent` / `type_hint` / `elements.body` に基づきレイアウト候補スコアを計算。
  - stage 5: `MappingStep` でも `ContentSlide` を参照し、layout 選定に利用。
  - API: `fastapi` 実装、スキーマ、ストレージが `ContentSlide` を保存単位として採用。
- 判断:
  - RM-046 以降はテンプレ独立のプレペアカードを唯一の成果物とし、`ContentSlide` は廃止する前提で計画を進める。
  - stage 4/5 や API では PrepareCard を受け取る構造が既に導入されているため、RM-046 の成果物をその仕様に合わせる。
  - 段階的移行は行わず、`ContentSlide` 依存コードを一括でリプレースするため、RM-046 の Plan で改修範囲を定義する。
- 対応:
  - 新モデル `PrepareCard`（仮称）を Stage3 で定義し、CLI・API・パイプラインの型定義を統一する。
  - `ContentSlide` 関連モジュール（モデル、検証、ストレージ、API スキーマ、パイプラインステップ）を廃止し、必要な場合は互換層を設けずに削除する。
  - 移行手順と影響範囲を `docs/design/stages/stage-02-prepare.md` および `docs/notes/20251017-content-approval-platform.md` に追記し、テスト更新計画を別途整理する。

## 提案するドキュメント更新
- `docs/requirements/stages/stage-02-prepare.md`: 入力を「プレペアソース」「AI プロンプト設定」「テンプレ独立カード構造」に再構成し、出力を `prepare_card` ベースへ更新。品質ゲートとログ要件もカード ID / バージョン軸で書き換える。
- `docs/design/stages/stage-02-prepare.md`: `SlideAIOrchestrator` の役割を「テンプレ依存 → プレペア抽象化」へ移行する設計図を追加。`PrepareCard` モデルと CLI オプション（`--prepare-source`, `-p/--page-limit` など）を反映する。
- `docs/design/schema/stage-02-prepare.md`: JSON スキーマを `prepare_card`・`story_context`・`supporting_materials[]` に改訂し、旧 `elements.title/body` の制約を撤廃。承認ログも `card_id` / `revision` 前提で書き換える。
- `docs/notes/20251017-content-approval-platform.md`: 新モデルとの差分と段階移行方針を追記（従来 `ContentSlide` 利用箇所の移行ガイド）。
- `docs/roadmap/roadmap.md`: RM-046 の「次アクション」を本調査内容に合わせて更新し、プレペア抽象化タスクを明確化。
- `samples/`: PrepareCard 用のサンプルセット（`prepare_card.sample.jsonc` など）を追加し、旧コンテンツ承認系のサンプルは `archive/` へ退避する方針をドキュメントに記載。

## 実装ロードマップ（案）
1. **Stage3 基盤更新**
   - `PrepareCard` モデルと関連スキーマを実装し、CLI `pptx prepare` / API / パイプライン（`SlideAIOrchestrator`, `ContentImportService`, `ContentApprovalStep`）を全て新モデルへ置換。
   - `uv run pptx prepare <prepare file>` をエントリに据え、旧 `spec_path` 引数と `ContentSlide` 依存コードを削除。
   - 既存テストの失敗箇所を洗い出し、後続ステップでの改修範囲を明確にする。
2. **ドキュメントとサンプルの整備**
   - 新サンプル／テストデータを追加し、既存ドキュメントを `PrepareCard` ベースへ更新。
3. **テストと移行**
   - CLI 統合テスト／API テストを新モデルで再構築し、旧成果物に依存するテストを廃止。
   - ドキュメント更新とサンプル差し替えを完了させた後、`ContentSlide` 系ファイルを削除。

## 検証方針（案）
- 単体: `PrepareCard` バリデーション、AI プロンプト生成、インポートサービス変換を pytest で網羅。
- CLI 統合: `uv run pptx prepare samples/contents/sample_import_content_summary.txt` を基準に生成物（`prepare_card.json`, `ai_generation_meta.json`, `prepare_log.json` など）を検証。
- API: FastAPI エンドポイントのスキーマ検証と ETag 制御を `httpx` ベースで確認。
- パイプライン: Stage3 内での PrepareCard 生成から承認ログ出力までを通しで確認し、既存 Stage4/5 入力との互換を検証する。

## 未決事項（次ステップで詰める）
- Prepare 入力フォーマット（JSON スキーマ vs. Markdown パーサ）の優先度。
- `config/slide_ai_policies.json` の再構成（章タイプ別テンプレート／プロンプト差し替え）と CLI オプション設計。
- 後方互換を切り捨てるにあたり、legacy コンテンツ承認 JSON を参照するテスト・ドキュメントの更新順序。
- API レイヤ (`src/pptx_generator/api/`) を抽象カードに合わせてどこまで同時改修するか。
