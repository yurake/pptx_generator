# RM-046 生成AIブリーフ構成自動化 初期調査（2025-11-02）

## 背景
- ロードマップ `RM-046 生成AIブリーフ構成自動化` の実装前調査として、現行の工程3（コンテンツ正規化）仕様と CLI 実装を確認。
- 既存仕様はテンプレート構造を前提とした `JobSpec.slides` を AI 入力に用いており、ロードマップが求める「テンプレ依存を排した抽象ブリーフ出力」と乖離している。

## 現行フロー整理
- `docs/requirements/stages/stage-03-content-normalization.md` は `content_approved.json` にテンプレ由来の `slide_id` / `intent` を維持する前提で記載。
- `src/pptx_generator/cli.py` の `pptx content` コマンド（1088 行付近）は、`ContentAIOrchestrator` が `JobSpec.slides` をベースに `ContentSlide` を生成し、`content_draft.json` を出力している。
- `ContentAIOrchestrator`（`src/pptx_generator/content_ai/orchestrator.py` 59-146 行）は各スライドのレイアウト名をプロンプト解決に使用し、レイアウトごとの `intent` をポリシーから取得している。
- `docs/design/schema/stage-03-content-normalization.md` は `elements.title/body` をレイアウトと 1:1 で結び付けるスキーマを想定し、ブリーフ抽象化は考慮されていない。

## ギャップと課題
- **テンプレ依存**: 現行は `layout` と `anchor` を前提としたスライド ID を保持し、テンプレ変更に引きずられる。RM-046 では章／メッセージ単位の抽象カードへ再設計する必要がある。
- **入力形態**: `pptx content` が常に `spec.json` を必須とするため、生情報（案件ブリーフ、取材メモ等）を直接流し込むフローを想定できない。
- **出力構造**: `ContentSlide.elements.body` の 40 文字×6 行制約はテンプレ向けに最適化されており、章骨子・メッセージ・支援コンテンツなど複数粒度を保持できない。
- **HITL ログ**: `content_review_log.json` はスライド ID ベースであり、抽象カード同士の結合／バージョン履歴を保持できる構造になっていない。
- **後工程整合**: 工程4（`docs/requirements/stages/stage-04-draft-structuring.md` 53 行付近）が `content_approved.json` のストーリー情報を参照する設計になっており、抽象カード化に合わせたプロパティ再定義が必要。

## 方向性メモ
- `pptx content` を「ブリーフビルダー」モードへ再定義し、`--brief-source`（JSON / Markdown / CSV）や `--brief-policy`（章構成プリセット）などテンプレ非依存の入力を受け付ける案。
- 新しい `BriefCard` モデル（`chapter`, `message`, `narrative`, `supporting_points[]`, `evidence_links[]`, `status` など）を `ContentSlide` から派生または置き換え、`story.phase` / `story.goal` を必須化する。
- HITL ログは `card_id` と `version`（ETag 相当）を持たせ、差戻し・再生成履歴を保持。AI 生成ログもカード単位で参照できるよう `ai_generation_meta.json` を再設計する。
- 後工程（RM-047）に引き継ぐため、章 → セクション → カードの階層構造と `layout_hint` へ渡すためのメタ情報（優先レイアウトカテゴリ、情報密度指標など）を定義する必要がある。
- スキーマ更新時は `docs/design/schema/stage-03-content-normalization.md` と `docs/requirements/stages/stage-03-content-normalization.md` を同時更新し、`samples/` 配下に新しい `content_draft.json` / `content_approved.json` を追加する。

## 提案するドキュメント更新
- `docs/requirements/stages/stage-03-content-normalization.md`: 入力を「ブリーフソース」「AI プロンプト設定」「テンプレ独立カード構造」に再構成し、出力を `brief_cards[]` ベースへ更新。品質ゲートとログ要件もカード ID / バージョン軸で書き換える。
- `docs/design/stages/stage-03-content-normalization.md`: `ContentAIOrchestrator` の役割を「テンプレ依存 → ブリーフ抽象化」へ移行する設計図を追加。`BriefCard` モデルと CLI オプション拡張（`--brief-source`, `--brief-policy`, `--card-limit` など）を反映する。
- `docs/design/schema/stage-03-content-normalization.md`: JSON スキーマを `brief_cards[]`・`story_context`・`supporting_materials[]` に改訂し、旧 `elements.title/body` の制約を撤廃。承認ログも `card_id` / `revision` 前提で書き換える。
- `docs/notes/20251017-content-approval-platform.md`: 新モデルとの差分と段階移行方針を追記（従来 `ContentSlide` 利用箇所の移行ガイド）。
- `docs/roadmap/roadmap.md`: RM-046 の「次アクション」を本調査内容に合わせて更新し、ブリーフ抽象化タスクを明確化。
- `samples/`: 新しい `content_draft_brief.jsonc` / `content_approved_brief.jsonc` を追加し、既存サンプルを `archive/` へ移動または名称変更する方針をドキュメントに記載。

## 未決事項（次ステップで詰める）
- Brief 入力フォーマット（JSON スキーマ vs. Markdown パーサ）の優先度。
- `config/content_ai_policies.json` の再構成（章タイプ別テンプレート／プロンプト差し替え）と CLI オプション設計。
- 後方互換を切り捨てるにあたり、既存 `content_approved.json` を参照するテスト・ドキュメントの更新順序。
- API レイヤ (`src/pptx_generator/api/`) を抽象カードに合わせてどこまで同時改修するか。
