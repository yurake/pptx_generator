# RM-046 生成AIブリーフ構成自動化 初期調査（2025-11-02）

## 背景
- ロードマップ `RM-046 生成AIブリーフ構成自動化` の実装前調査として、現行の工程3（コンテンツ準備）仕様と CLI 実装を確認。
- 既存仕様はテンプレート構造を前提とした `JobSpec.slides` を AI 入力に用いており、ロードマップが求める「テンプレ依存を排した抽象ブリーフ出力」と乖離している。

## 現行フロー整理（旧仕様の確認）
- 当時の `docs/requirements/stages/stage-03-content-normalization.md` は従来のコンテンツ承認 JSON（テンプレ由来の `slide_id` / `intent` を維持）を前提に記載されていた（現在は BriefCard ベースへ更新済み）。
- `src/pptx_generator/cli.py` の `pptx prepare` コマンド（旧実装）は `ContentAIOrchestrator` が `JobSpec.slides` から `ContentSlide` を生成し、`content_draft.json` を出力していた。
- `ContentAIOrchestrator`（当時の `src/pptx_generator/content_ai/orchestrator.py` 59-146 行）は各スライドのレイアウト名をプロンプト解決に使用し、レイアウトごとの `intent` をポリシーから取得していた。
- `docs/design/schema/stage-03-content-normalization.md` も `elements.title/body` をレイアウトと 1:1 で結び付けるスキーマを想定しており、ブリーフ抽象化は考慮されていなかった。

## ギャップと課題
- **テンプレ依存**: 現行は `layout` と `anchor` を前提としたスライド ID を保持し、テンプレ変更に引きずられる。RM-046 では章／メッセージ単位の抽象カードへ再設計する必要がある。
- **入力形態**: `pptx prepare` が常に `spec.json` を必須とするため、生情報（案件ブリーフ、取材メモ等）を直接流し込むフローを想定できない。
- **出力構造**: `ContentSlide.elements.body` の 40 文字×6 行制約はテンプレ向けに最適化されており、章骨子・メッセージ・支援コンテンツなど複数粒度を保持できない。
- **HITL ログ**: `content_review_log.json` はスライド ID ベースであり、抽象カード同士の結合／バージョン履歴を保持できる構造になっていない。
- **後工程整合**: 旧工程4（当時の `docs/requirements/stages/stage-04-draft-structuring.md` 53 行付近）が legacy コンテンツ承認 JSON のストーリー情報を参照する設計になっており、抽象カード化に合わせたプロパティ再定義が必要。

## 方向性メモ
- `pptx prepare` を「ブリーフビルダー」モードへ再定義し、テンプレ非依存の入力（`--brief-source` など）を受け付ける案。ポリシーは既定値固定で扱う。
- 新しい `BriefCard` モデル（`chapter`, `message`, `narrative`, `supporting_points[]`, `evidence_links[]`, `status` など）を `ContentSlide` から派生または置き換え、`story.phase` / `story.goal` を必須化する。
- HITL ログは `card_id` と `version`（ETag 相当）を持たせ、差戻し・再生成履歴を保持。AI 生成ログもカード単位で参照できるよう `ai_generation_meta.json` を再設計する。
- 後工程（RM-047）に引き継ぐため、章 → セクション → カードの階層構造と `layout_hint` へ渡すためのメタ情報（優先レイアウトカテゴリ、情報密度指標など）を定義する必要がある。
- スキーマ更新時は `docs/design/schema/stage-03-content-normalization.md` と `docs/requirements/stages/stage-03-content-normalization.md` を同時更新し、`samples/` 配下に BriefCard 前提のサンプル（例: `samples/prepare/prepare_card.sample.jsonc`）を追加する。

## CLI インターフェース検討
- 要望: `uv run pptx prepare <brief file>` でブリーフ入力を直接指定し、従来必須だった `spec.json` 引数を不要化する。
- 影響:
  - `src/pptx_generator/cli.py` の `content` コマンド定義（~1040-1260 行）でポジショナル引数 `spec_path` を廃止し、新たに `brief_path`（必須）を受け取る設計へ変更。
  - Spec 情報が必要な処理（例: `ContentApprovalStep` で既存 spec を適用する分岐）は RM-047 以降に委譲する前提で整理。従来の `--content-approved` / `--content-review-log` は Brief モードでは使用不可と明記する。
  - `ContentImportService` を経由した複数ソース取り込みは `brief_path` の拡張（JSON で複数参照を列挙する等）として別途検討する。
- TODO: コマンドリファレンス（README, docs/runbooks/, docs/requirements/stages/stage-03-content-normalization.md）で新シグネチャを反映し、サンプルコマンドを更新する。

## ContentSlide の扱い整理
- 依存箇所:
  - 工程3: `BriefAIOrchestrator`, `BriefNormalizationStep`, API ストア（`BriefStore`）が `BriefCard` を前提に動作。
  - 工程4: `DraftStructuringStep` が `ContentSlide` の `intent` / `type_hint` / `elements.body` に基づきレイアウト候補スコアを計算。
  - 工程5: `MappingStep` でも `ContentSlide` を参照し、layout 選定に利用。
  - API: `fastapi` 実装、スキーマ、ストレージが `ContentSlide` を保存単位として採用。
- 判断:
  - RM-046 以降はテンプレ独立のブリーフカードを唯一の成果物とし、`ContentSlide` は廃止する前提で計画を進める。
  - 工程4/5 や API で利用している `ContentSlide` についても、RM-047 で刷新する `BriefCard` ベースの構造へ置き換える。
  - 段階的移行は行わず、`ContentSlide` 依存コードを一括でリプレースするため、RM-046/047 の Plan で合わせて改修範囲を定義する。
- 対応:
  - 新モデル `BriefCard`（仮称）を Stage3 で定義し、CLI・API・パイプラインの型定義を統一する。
  - `ContentSlide` 関連モジュール（モデル、検証、ストレージ、API スキーマ、パイプラインステップ）を廃止し、必要な場合は互換層を設けずに削除する。
  - 移行手順と影響範囲を `docs/design/stages/stage-03-content-normalization.md` および `docs/notes/20251017-content-approval-platform.md` に追記し、テスト更新計画を別途整理する。

## 提案するドキュメント更新
- `docs/requirements/stages/stage-03-content-normalization.md`: 入力を「ブリーフソース」「AI プロンプト設定」「テンプレ独立カード構造」に再構成し、出力を `prepare_card` ベースへ更新。品質ゲートとログ要件もカード ID / バージョン軸で書き換える。
- `docs/design/stages/stage-03-content-normalization.md`: `ContentAIOrchestrator` の役割を「テンプレ依存 → ブリーフ抽象化」へ移行する設計図を追加。`BriefCard` モデルと CLI オプション（`--brief-source`, `--card-limit` など）を反映する。
- `docs/design/schema/stage-03-content-normalization.md`: JSON スキーマを `prepare_card`・`story_context`・`supporting_materials[]` に改訂し、旧 `elements.title/body` の制約を撤廃。承認ログも `card_id` / `revision` 前提で書き換える。
- `docs/notes/20251017-content-approval-platform.md`: 新モデルとの差分と段階移行方針を追記（従来 `ContentSlide` 利用箇所の移行ガイド）。
- `docs/roadmap/roadmap.md`: RM-046 の「次アクション」を本調査内容に合わせて更新し、ブリーフ抽象化タスクを明確化。
- `samples/`: BriefCard 用のサンプルセット（`prepare_card.sample.jsonc` など）を追加し、旧コンテンツ承認系のサンプルは `archive/` へ退避する方針をドキュメントに記載。

## 実装ロードマップ（案）
1. **Stage3 基盤更新**
   - `BriefCard` モデルと関連スキーマを実装し、CLI `pptx prepare` / API / パイプライン（`ContentAIOrchestrator`, `ContentImportService`, `ContentApprovalStep`）を全て新モデルへ置換。
   - `uv run pptx prepare <brief file>` をエントリに据え、旧 `spec_path` 引数と `ContentSlide` 依存コードを削除。
   - 新サンプル／テストデータを追加し、既存テストを `BriefCard` 前提に改修。
2. **Stage4/5・API 同期（RM-047 連携）**
   - Draft/Mapping パイプラインを `BriefCard` ベースで再設計し、`layout_hint` 算出やセクション構造を章メタ情報から導出。
  - `BriefStore` を中心とした FastAPI スキーマを整備し、旧 Content API を廃止する。
3. **テストと移行**
   - CLI 統合テスト／API テストを新モデルで再構築し、旧成果物に依存するテストを廃止。
   - ドキュメント更新とサンプル差し替えを完了させた後、`ContentSlide` 系ファイルを削除。

## 検証方針（案）
- 単体: `BriefCard` バリデーション、AI プロンプト生成、インポートサービス変換を pytest で網羅。
- CLI 統合: `uv run pptx prepare samples/contents/sample_import_content_summary.txt` を基準に生成物（`prepare_card.json`, `ai_generation_meta.json`, `brief_log.json` など）を検証。
- API: FastAPI エンドポイントのスキーマ検証と ETag 制御を `httpx` ベースで確認。
- パイプライン: Stage4/5 連携テストを後続タスク（RM-047）で再構成し、`layout_hint` 一貫性をチェックする。

## 未決事項（次ステップで詰める）
- Brief 入力フォーマット（JSON スキーマ vs. Markdown パーサ）の優先度。
- `config/content_ai_policies.json` の再構成（章タイプ別テンプレート／プロンプト差し替え）と CLI オプション設計。
- 後方互換を切り捨てるにあたり、legacy コンテンツ承認 JSON を参照するテスト・ドキュメントの更新順序。
- API レイヤ (`src/pptx_generator/api/`) を抽象カードに合わせてどこまで同時改修するか。
