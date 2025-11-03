# 工程2 コンテンツ正規化 (HITL) 設計

## 目的
- ブリーフ入力（Markdown / JSON など）を BriefCard モデルへ整形し、後続工程が直接利用できる構造化データを提供する。
- AI 生成と HITL 承認を組み合わせ、監査可能なログと統計情報を残す。
- `.brief/` 配下に成果物を集約し、工程3 の `pptx compose` がそのまま参照できるようにする。

## システム構成
| レイヤ | コンポーネント | 概要 |
| --- | --- | --- |
| CLI | `pptx content` | Brief ソースを読み込み、BriefCard 生成・評価・監査ログ出力を実行 |
| サービス層 | `BriefAIOrchestrator` | ポリシーに基づいてカードを生成し、AI ログと統計を返す |
| モデル層 | `BriefDocument` / `BriefCard` | Pydantic モデルで JSON スキーマを表現 |
| ストレージ | Brief Store | `.brief/brief_cards.json` など成果物一式を保存 |

## データモデル
- `BriefDocument`: `brief_id`, `cards[]`, `meta`。
- `BriefCard`: `card_id`, `chapter`, `message`, `narrative`, `supporting_points`, `story.phase`, `intent_tags`, `status`, `autofix_applied`。
- `BriefGenerationMeta`: `policy_id`, `generated_at`, `input_hash`, `cards[]`, `statistics`。
- `BriefAuditLog`: 生成時刻・成果物パス・統計値をまとめた監査メタ。

## ワークフロー
1. CLI がブリーフ入力（Markdown / JSON）を読み込み、`brief_source` として渡す。
2. `BriefAIOrchestrator` がポリシーを選択し、LLM（またはモック）でカード候補を生成。
3. 生成カードとログを `.brief/` に書き出し、統計情報を `ai_generation_meta.json` に記録。
4. 監査ログ (`audit_log.json`) に成果物パスと SHA256 ハッシュ（将来拡張）を残す。
5. 工程3 では `--brief-cards`, `--brief-log`, `--brief-meta` を指定して再利用する。差戻し時はカード編集または再生成を実施。

## CLI (`pptx content`)
- パラメータ
  | オプション | 説明 | 既定値 |
  | --- | --- | --- |
  | `<brief_path>` | 入力ブリーフ（Markdown / JSON） | 必須 |
  | `--output <dir>` | 成果物ディレクトリ | `.brief` |
  | `--card-limit <int>` | 生成するカード枚数の上限 | 指定なし |
- 代表的な出力
  - `brief_cards.json`
  - `brief_log.json`
  - `brief_ai_log.json`
  - `ai_generation_meta.json`
  - `brief_story_outline.json`
  - `audit_log.json`

## ログと監査
- `brief_ai_log.json`: プロンプトテンプレート、利用モデル、警告（`llm_stub` 等）、トークン消費量を記録。
- `ai_generation_meta.json`: カードごとの `content_hash` や `story_phase` を持ち、工程3での差分検出に利用。
- `audit_log.json`: 生成時刻・ポリシー ID・成果物のパスをまとめる。今後ハッシュ値を追加し改ざん検知を強化する。

## エラーハンドリング
- ブリーフ入力が存在しない場合は exit code 2 (`FileNotFoundError`)。
- ポリシー読み込みに失敗した場合は exit code 4 (`BriefPolicyError`)。
- LLM 実行でリトライ不能なエラーが発生した場合は exit code 4。警告のみの場合は `brief_ai_log.json` に記録し処理を継続する。

## 今後の拡張アイデア
- HITL 補正用の簡易 UI と `brief_log.json` 編集 API を検討（`docs/roadmap/roadmap.md` RM-051 を参照）。
- 章テンプレートに応じたカードの自動再構成／統合を `BriefCardRefiner` として追加。
- ブリーフの差分比較（再生成時の変更検出）を `ai_generation_meta.json` のハッシュ比較で自動化。
