# layout_ai policy 拡張検討メモ（2025-11-22）

## 背景
- RM-064 で Stage3 に `ContentSlide.source`（story_phase / intent_tags / Blueprint）を導入し、Layout AI 呼び出しやヒューリスティックへメタデータを渡せるようにした。
- 一方 `config/layout_ai_policies.json` は単一の `prompt_template` のみを保持しており、canonical usage tags や Prepare 由来メタをプロンプトへ伝える手段がない。
- ToDo では「policy 拡張検討」「usage_tags 記述と整合」「canonical usage tags をプロンプトへ組み込む」等の未対応項目が残っている。

## 現状整理
- **ポリシー構造**: `config/layout_ai_policies.json` は `layout-default` 1 件で、`prompt_template` には「候補を 0〜1 評価して並べる」指示のみ。レイアウト別設定（`slide_policies`）も空で、Usage Tags を明示する仕組みがない。
- **使用語彙**: canonical usage tags は `config/usage_tags.json` に intent / media / fallback で定義。`utils/usage_tags.py` で正規化しており Stage1/Stage3 の共通語彙として利用中。
- **メタデータ**: `CardLayoutRecommender` から Layout AI へ渡せる値として、今回追加した `card_payload["source"]` および `layout_metadata`（usage_tags_rule / text_hint / media_hint / placeholder_summary）を既に構築済み。ただし prompt 内での説明は policy 依存。
- **ドキュメント**: usage tags の整理メモ（`docs/notes/20251109-usage-tags-scoring.md`）や RM-054 設計書では canonical 語彙を参照する旨を記載しているが、Layout AI policy との連携方法は未定義。

## 課題
1. ポリシー JSON に canonical usage tags・Blueprint 由来ヒントを織り込む項目がなく、メタデータを prompt へ安全に流し込めない。
2. Stage1/Stage3 の Usage Tags 説明が `config/usage_tags.json` に散在しており、policy から参照するガイドラインが不足。
3. Layout AI prompt が ID とスコア指示のみのため、LLM が story_phase / intent_tags / template constraints を理解している前提になっている。

## 提案
### 1. ポリシー JSON 拡張案
- `layout_ai_policies.json` に以下のキー追加を検討:
  - `usage_tags_template`: canonical usage tags とその説明をまとめたテンプレート文字列（`usage_tags.json` と連動）。
  - `card_context_template`: `ContentSlide.source` や Blueprint 情報を組み込む際のテンプレート（例: `{{primary_intent}}`, `{{story_phase}}`, `{{blueprint_slots}}`）。
  - `layout_metadata_template`: `layout_metadata` 内の usage_tags_rule / text_hint / media_hint を展開するための書式。
- 既存スキーマとの後方互換を保つため、上記フィールドはオプショナルにし、未設定時は現在の挙動（単純な `prompt_template`）を維持する。

### 2. Usage Tags ドキュメント連携
- `config/usage_tags.json` の説明を policy から参照するため、以下を整備:
  - `docs/notes/20251109-usage-tags-scoring.md` に canonical usage tags と Layout AI policy の関係（意図タグ / メディアタグ / フォールバックの利用方法）を追記。
  - `config/usage_tags.json` 更新時に policy へも反映する運用手順を `docs/policies/config-and-templates.md` または `docs/runbooks/` に記載。

### 3. プロンプト設計方針
- `prompt_template` に以下の情報を明示的に含める:
  - `card` 情報: story_phase, intent_tags, Blueprint slot 必須/任意、想定文字量。
  - `canonical_usage_tags`: intent / media の定義一覧を bullet 形式で列挙（policy か共通テンプレートで注入）。
  - `layout_metadata`: 各候補の usage_tags_rule・テキスト/メディアヒント・placeholder summary を JSON もしくは表形式で提示。
  - 出力形式: `recommended` 1 件 + `classifications`（canonical intent / media）を明文化。既存レスポンスの JSON 形式に沿う指示を保つ。

## 次アクション
1. `layout_ai/policy.py` と `config/layout_ai_policies.json` のスキーマ拡張案を設計し、後方互換条件を整理（新旧併存期間を想定）。
2. canonical usage tags と policy テンプレートを連携する共通テンプレート（Jinja など）の導入可否を調査（複数ポリシー対応を考慮）。
3. 上記内容を ToDo（layout_ai policy 拡張検討）のサブタスクに反映し、実装フェーズで必要なテスト（prompt 生成の snapshot など）を洗い出す。

## 実施内容メモ（2025-11-22）
- `layout_ai/policy.py` に `usage_tags_template` / `card_context_template` を追加し、ポリシーごとにメタデータセクションの文面を制御できるようにした。
- `config/layout_ai_policies.json` にデフォルトテンプレートを追加し、Layout AI へ用途タグ説明・カード文脈を明示的に渡す設定を反映。
- `layout_ai/client.py` の `_build_user_prompt` を拡張し、上記テンプレートに基づいて `usage_tags_prompt` / `card_context_prompt` を生成。あわせて構造化データ（usage_tags_reference / card_context）を payload に内包。
- slide_ai ログのフォーマッタを刷新し、ファイル出力に加えて標準出力にも同内容を流しつつ、LLM リクエスト／レスポンス以外の雑多なログはフィルタで抑制した（2025-11-24 追記）。
- `card_context` 経由の付帯情報は削除し、カード本体と usage_tags で重複するデータを送らない設計へ変更（2025-11-24 更新）。
- Stage3 側で追加した `allowed_tags_detail` や `ContentSlide.source` を活用し、LLM が canonical usage tags とカード背景を参照したうえで評価できる状態に更新済み。
