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
