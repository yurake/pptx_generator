# stage 2 コンテンツ準備 (HITL) 設計

## 目的
- プレペア入力（Markdown / JSON など）を PrepareCard モデルへ整形し、後続 stage が直接利用できる構造化データを提供する。
- AI 生成と HITL 承認を組み合わせ、監査可能なログと統計情報を残す。
- `.pptx/prepare/` 配下に成果物を集約し、stage 3 の `pptx compose` がそのまま参照できるようにする。

## システム構成
| レイヤ | コンポーネント | 概要 |
| --- | --- | --- |
| CLI | `pptx prepare` | Prepare ソースを読み込み、PrepareCard 生成・評価・監査ログ出力を実行 |
| サービス層 | `PrepareAIOrchestrator` (`src/pptx_generator/prepare_ai/orchestrator.py`) + `ContentAIOrchestrator` | 章単位で LLM を呼び出し、カードを生成。AI ログと統計を返す |
| モデル層 | `PrepareDocument` / `PrepareCard` | Pydantic モデルで JSON スキーマを表現 |
| ストレージ | Prepare Store | `.pptx/prepare/prepare_card.json` など成果物一式を保存 |

## データモデル
- `PrepareDocument`: `prepare_id`, `cards[]`, `meta`。
- `PrepareCard`: `card_id`, `order`, `role.story_phase`, `role.intent_tags`, `content.title`, `content.headline`, `content.body[]`, `content.notes[]`, `meta`。
- `PrepareGenerationMeta`: `policy_id`, `generated_at`, `input_hash`, `cards[]`, `statistics`。
- `PrepareAuditLog`: 生成時刻・成果物パス・統計値をまとめた監査メタ。

## ワークフロー
1. CLI がプレペア入力（Markdown / JSON）を読み込み、`prepare_source` として渡す。
2. `PrepareAIOrchestrator`（`src/pptx_generator/prepare_ai/orchestrator.py`）がポリシーを選択し、LLM（またはモック）でカード候補を生成。
3. 生成カードとログを `.pptx/prepare/` に書き出し、統計情報を `ai_generation_meta.json` に記録。
4. 監査ログ (`audit_log.json`) に成果物パスと SHA256 ハッシュ（将来拡張）を残す。
5. stage 3 では `--prepare-cards` を指定するだけで、`prepare_card.json.meta` に記録されたログ／AIメタのパスを再利用する。差戻し時はカード編集または再生成を実施。

## CLI (`pptx prepare`)
- パラメータ
  | オプション | 説明 | 既定値 |
  | --- | --- | --- |
  | `<prepare_path>` | 入力プレペア（Markdown / JSON） | 必須 |
  | `--output <dir>` | 成果物ディレクトリ | `.pptx/prepare` |
  | `-p/--page-limit <int>` | 生成するカード枚数の上限 | 指定なし |
- 代表的な出力
  - `prepare_card.json`
  - `prepare_log.json`
  - `prepare_ai_log.json`
  - `ai_generation_meta.json`
  - `prepare_story_outline.json`
  - `audit_log.json`

## ログと監査
- `prepare_ai_log.json`: プロンプトテンプレート、利用モデル、警告（`response_not_json` や `body_not_array` など）、トークン消費量を記録。
- `ai_generation_meta.json`: カードごとの `content_hash` や `story_phase` を持ち、stage 3 での差分検出に利用。
- `audit_log.json`: 生成時刻・ポリシー ID・成果物のパスをまとめる。今後ハッシュ値を追加し改ざん検知を強化する。

## エラーハンドリング
- プレペア入力が存在しない場合は exit code 2 (`FileNotFoundError`)。
- ポリシー読み込みに失敗した場合は exit code 4 (`PreparePolicyError`)。
- LLM 実行でリトライ不能なエラーが発生した場合は exit code 4。警告のみの場合は `prepare_ai_log.json` に記録し処理を継続する。

## 今後の拡張アイデア
- HITL 補正用の簡易 UI と `prepare_log.json` 編集 API を検討（`docs/roadmap/roadmap.md` RM-051 を参照）。
- 章テンプレートに応じたカードの自動再構成／統合を `PrepareCardRefiner` として追加。
- プレペアの差分比較（再生成時の変更検出）を `ai_generation_meta.json` のハッシュ比較で自動化。
