# レイアウト AI 候補メタ情報不足の調査

## 背景
- 工程3（`pptx compose`）では LLM を用いてレイアウト候補をスコアリングしている。
- ユーザーから、LLM に渡すレイアウト情報が ID の配列のみで、レイアウト構造を判断する材料が不足しているとの指摘があった。

## 現状確認
- `_build_user_prompt` で組み立てる payload は以下の通り。`candidate_layouts` はレイアウト ID のみを渡している。  
  `src/pptx_generator/layout_ai/client.py:703-709`
  ```json
  {
    "card": { ... },
    "candidate_layouts": ["title", "section_cover_left", ... ],
    "instruction": "<policy で定義されたプロンプト>"
  }
  ```
- レイアウト候補を構築する `CardLayoutRecommender._apply_layout_ai` では `LayoutProfile` から `layout_id` だけを抽出。`layout_name` や `usage_tags`、`text_hint` 等は送られていない。  
  `src/pptx_generator/draft_recommender.py:205-239`
- `LayoutProfile` には以下のメタ情報が存在し、レイアウト判定の拡充に活用可能。  
  `src/pptx_generator/draft_recommender.py:32-60`
  - `layout_name`
  - `usage_tags`（意図・配置の語彙）
  - `text_hint`（最大行数など）
  - `media_hint`（テーブル可否など）

## 課題
- LLM がレイアウト ID だけで判断するため、同義語や命名揺れの影響が大きい。
- レイアウト構造・収容力・メディア可否といった定量的情報を参照できず、スコアリング精度や説明責務が不足する。
- ポリシー側でレイアウト別プロンプトを用意しても、ID 以外のヒントがないため意味付けが困難。

## 想定論点
- レイアウト候補ごとに `usage_tags` や `text_hint` を添付し、LLM が構造・制約を推定できるようにする。
- `layouts.jsonl` から抜粋した図形構成やアンカー情報も要約して付与する方法の検討。
- レイアウト名や説明文の標準化（i18n 対応や別表管理）によるノイズ低減。
- 既存 policy / prompt との下位互換を保ちつつ、追加メタ情報を扱えるスキーマ設計。

## 次ステップ案
- 新規 RM（仮称: RM-064 レイアウト候補メタ情報拡充）を起票し、以下をスコープ化する。
  - LLM へ渡す候補データ構造の再設計（ID + メタ情報）
  - `LayoutProfile` から抽出する属性の洗い出しとシリアライズ形式の検討
  - ポリシーおよびテストの調整、スコアリング結果の説明可能性向上策
- ToDo 起票時には `docs/todo/` テンプレートに従い、詳細タスクを分解する。
