# 用途タグ体系再設計（Draft） 2025-11-22

## 背景
- Stage1（template_ai / prepare）と Stage3（layout_ai / draft_structuring / mapping）で `canonical usage tags` を参照するが、Intent / Media の語彙が増え、タグ説明やシノニム運用が散在している。
- RM-064 では Layout AI とヒューリスティックが `ContentSlide.source` や `allowed_tags_detail` を参照できるようになったが、タグ体系は従来のまま。Intent と Media を二軸で整理し直し、Stage1/Stage3 での整合を図る必要がある。
- ToDo には「usage_tags 記述と `config/usage_tags.json` の説明を連携」「canonical usage tags の共通利用」「体系再設計」の未完タスクが残っている。

## 現状整理
- `config/usage_tags.json`: intent_tags / media_tags / fallback_tag / static_rules を定義。説明文は日本語で記載。CI は `utils/usage_tags.py` を通じてこの語彙を正規化。
- `template_ai`（Stage1）: usage tags を LLM へ提示し、テンプレ抽出時に `usage_tags` を得る。タグ語彙の説明は current config 依存。
- `layout_ai`（Stage3）: `allowed_tags_detail` を利用して canonical 説明を prompt へ供給。従来タグの synonyms は `utils/usage_tags.py` の `_SYNONYM_MAP` に限定。
- `docs/notes/20251109-usage-tags-scoring.md`: usage tags の抽出ロジックや課題を整理。タグ語彙の見直し（title の乱用抑制など）を将来の課題として記載。
- `mapping` や CLI ログでは usage tags を表記するが、Intent と Media の区別や階層がなく、利用者への説明が不足。

## 課題
1. Intent と Media の区別が曖昧で、タグ名の重複・意味のブレを生みやすい（例: `summary`, `overview`, `content`）。  
2. Stage1 の AI プロンプト、Stage3 の Layout AI、ヒューリスティック／ログに一貫したタグ説明を表示する仕組みがない。  
3. 新タグ追加時の運用手順（config 更新 → AI プロンプト → validation）が文書化されていない。  
4. `_SYNONYM_MAP` や static_rules が増えるほど保守が難しく、タグ説明を利用者に可視化しづらい。

## 再設計方針（案）
1. **二軸構造の明確化**  
   - Intent: スライドの目的や位置付けを表すタグ（`title`, `agenda`, `overview`, `content`, `summary`, `closing`, `next_steps`, `call_to_action` 等）。  
   - Media: 表現形式（`chart`, `table`, `visual`, `mixed` 等）。  
   - Fallback: 意図不明/未定義（`generic`）を維持。  
   - JSON 構造を `intent`, `media`, `fallback`, `synonyms`, `deprecated` 等へ整理し、将来的に Yaml への移行も視野に入れる。

2. **説明／シノニムの強化**  
   - 各タグに `description` のほか `examples`, `synonyms`, `recommended_usage` を持たせ、AI プロンプトとログ表示で活用可能にする。  
   - `_SYNONYM_MAP` を `config/usage_tags.json` へ移し、人為的に増やす際の変更点を一本化。  
   - static_rules はテンプレ抽出時のヒューリスティックとして独立セクション化（`layout_name_rules` など）。

3. **運用フロー整備**  
   - `docs/policies/config-and-templates.md` に usage tags 更新手順（config 修正 → テスト → policy 反映）を追加。  
   - 変更時にまわすテスト（`tests/test_utils_usage_tags.py`, `tests/test_layout_recommender.py`, Stage1/Stage3 integration）を列挙し、Checklist 化する。

4. **表示・監査の改善**  
   - Layout AI / template AI の prompt へ Intent と Media の説明文を明示的に差し込み、タグ語彙の理解を支援。  
   - `draft_mapping_log.json` や CLI でタグ説明を表示するオプションを検討（例: verbose モード）。  
   - `diagnostics.json` でタグ出現頻度や未知タグを可視化し、体系更新の判断材料にする。

## 影響範囲（想定）
- `config/usage_tags.json` のスキーマ変更（バージョン付与、Synonym 設定追加）。  
- `utils/usage_tags.py` の正規化ロジック更新（synonym map, fallback, intent/media 分類）。  
- Stage1 (`template_ai`, `prepare`)、Stage3 (`layout_ai`, `draft_recommender`, `mapping`)、テスト群のタグ参照箇所。  
- ドキュメント更新（usage tags メモ、config policies、ToDo）。  
- 将来的には Stage1/Stage3 のプロンプト整合を取ることで、タグ拡張時のメンテを容易化。

## 次のステップ候補
1. `config/usage_tags.json` の新スキーマ案を具体化（Intent / Media / Synonym / Deprecated 等）。  
2. `utils/usage_tags.py` のリファクタリング計画を策定（テスト追加、Synonym map 移行）。  
3. Stage1/Stage3 プロンプトへ反映するテンプレート提案（既存 policy テンプレートとの統合）を作成。  
4. ログ・診断出力の改善案（タグ説明表示、Unknown タグ集計）を検討。  
5. 上記を踏まえ、実装タスクを ToDo の該当項目（用途タグ体系の再設計）に反映し、必要なサブタスクを起票する。

---

## 対象整理

| 領域 | ファイル / コンポーネント | 目的 / 影響 |
| --- | --- | --- |
| 共通設定 | `config/usage_tags.json` | Intent / Media 二軸の再定義、説明・同義語・廃止タグ管理。バージョン付与を検討。 |
| 共通ユーティリティ | `src/pptx_generator/utils/usage_tags.py` | 新スキーマ対応・Synonym map の外部化・正規化ロジック更新。 |
| Stage1 テンプレ抽出 | `src/pptx_generator/template_ai/*`, `config/template_ai_policies.json` | AI プロンプトに新しい Intent/Media 語彙を渡し、Template AI が canonical タグを返せるようにする。 |
| Stage1 Prepare | `src/pptx_generator/prepare/*` | `PrepareCard` の intent_tags / role を新体系へ合わせる（必要に応じ Blueprint モードを調整）。 |
| Stage3 レコメンド | `src/pptx_generator/draft_recommender.py`, `layout_ai/client.py`, `pipeline/mapping.py` | Layout AI・ヒューリスティック・マッピングログで Intent/Media を区別し、説明文を表示できるようにする。 |
| テスト | `tests/test_utils_usage_tags.py`, `tests/test_layout_recommender.py`, `tests/test_template_ai.py` など | 新タグ体系の正規化・AI 応答の整合性検証。 |
| ドキュメント | `docs/notes/20251109-usage-tags-scoring.md`, `docs/policies/config-and-templates.md` | タグ体系・更新手順を追記し、運用の基準を統一。 |

## 設計方針（詳細）

1. **JSON スキーマ拡張**  
   - `intent_categories` / `media_categories` といったトップレベルで Intent / Media を明示。  
   - タグごとに `synonyms`, `examples`, `deprecated`, `replacement` を保持。  
   - static_rules を `layout_rules.intent` / `layout_rules.media` へ分割し、テンプレ抽出時に活用。
2. **ユーティリティ更新**  
   - `_SYNONYM_MAP` を廃止し、新スキーマから読み込むようリファクタ。  
   - Intent / Media を返すヘルパー（例: `normalize_intent_tags`, `normalize_media_tags`）を追加し、Stage1/Stage3 が明示的に呼ぶ。  
   - Fallback と deprecated tags をログに記録し、CI で検出可能にする。
3. **プロンプト整合**  
   - Template AI / Layout AI の policy テンプレートに Intent / Media のリストと説明文を埋め込み、共通語彙を共有。  
   - Stage3 の `allowed_tags_detail` を Intent / Media で構造化し、LLM が用途と表現の両軸を理解できるようにする。
4. **診断とログ**  
   - `diagnostics.json` に Intent / Media 別のタグ分布、Unknown/Deprecated の検出結果を追加。  
   - CLI ログ（outline, compose）に `--show-tag-description` オプションを設け、タグ説明を確認できるようにする案を検討。

## テスト戦略（詳細）

1. **ユニットテスト**  
   - `tests/test_utils_usage_tags.py`: 新スキーマでの正規化（Intent / Media / Synonym / Deprecated）を網羅。  
   - `tests/test_template_ai.py`: Template AI が新体系で canonical タグを返すことを確認。  
   - `tests/test_layout_recommender.py`: Layout AI に渡す `allowed_tags_detail` が Intent / Media を区別して提示されるか検証。
2. **統合テスト**  
   - `tests/test_cli_integration.py`: `pptx template` → `pptx compose` → `pptx gen` フローでタグ体系変更後も成功することを確認。  
   - `tests/test_cli_prepare.py`: Blueprint / Dynamic モードそれぞれで意図タグが期待通りになるか確認。
3. **リグレッションチェック**  
   - `uv run pptx tpl-extract` の出力（`layouts.jsonl`）に追加メタが不要なことを確認。  
   - `diagnostics.json` / `draft_mapping_log.json` にタグ説明が反映される場合のスナップショットテストを検討。
