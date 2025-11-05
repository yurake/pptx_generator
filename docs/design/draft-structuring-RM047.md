# RM-047 工程4ドラフト構成設計リニューアル設計書

## 背景と目的
- 工程3で確定した `brief_cards.json`（テンプレ依存を排したブリーフカード集合）と、工程2で抽出した `jobspec.json`（テンプレ構造とプレースホルダ情報）を統合し、工程5が期待する `generate_ready.json` を工程4で生成する。
- 既存の `draft_draft.json` / `draft_approved.json` / `rendering_ready.json` を前提としたフローを廃止し、工程4→5 の受け渡しを `generate_ready` 基盤へ全面移行する。
- 生成AIがカード単位でスライド割当提案を行い、HITL による承認・差戻し操作と連携できる構造へ再設計する。

## 入出力
### 入力
- `brief_cards.json`: 工程3 の成果物。`cards[*]` に `card_id`, `chapter`, `message`, `story.phase`, `intent_tags` などを保持。
- `brief_log.json`, `ai_generation_meta.json`: 生成経緯・HITL 操作のログ。必須ではないが、差戻し理由や AI の使用メタを参照するために読み込む。
- `jobspec.json`: 工程2 で管理するテンプレ構造データ。`slides[*]` に `layout`, `anchor`（図形名）, `textboxes` / `tables` / `images` 等のプレースホルダ情報を保持。
- `layouts.jsonl`: レイアウトカテゴリのメタ（用途タグ、テキスト収容量、メディア許容フラグなど）。
- `analysis_summary.json`（任意）: 工程6（Analyzer）の結果。重大度別件数やレイアウト整合性をカード割当時に参照する。
- 章テンプレ辞書（任意）: `config/chapter_templates/<pattern>/<id>.json`。章構成の整合チェックに利用する。

### 出力
- `generate_ready.json`: 工程5 がレンダリングに利用する唯一の構成ファイル。`slides[*]` には `layout_id`, `elements`, `meta`（章情報や割当元カード ID）を含める。
- `generate_ready_meta.json`: 主に HITL と運用向けのメタ情報。章テンプレ適合率、カード割当結果、Analyzer 指摘要約、AI 推薦の適用件数などを記録。
- `mapping_log.json`: カード単位の割当プロセスログ。選定した `layout_id`、候補スコア、AI 推薦内容、HITL アクションを保持する。
- `draft_review_log.json`: 工程4 HITL 操作ログ（承認・差戻し・付録送り）。既存仕様のフィールドを維持しつつ `generate_ready` 向けに再定義。

## プロセス概要
1. **Brief 読み込み**: `BriefNormalizationStep` が `brief_cards` / `brief_log` / `ai_generation_meta` を読み込み、`PipelineContext` に `brief_document` を格納する。
2. **カードメタ抽出**: 各カードの `story.phase`, `intent_tags`, `supporting_points` からテンプレ選定に必要な特徴量を生成する（用途タグ、情報密度、証憑数など）。
3. **ジョブスペック参照**: `jobspec.slides[*]` を `layout_id` キーでインデックス化し、アンカー構造やプレースホルダ数を計算する。`layouts.jsonl` が存在する場合は用途タグ・容量ヒントを補完する。
4. **AI 推薦（カード単位）**:
   - `CardLayoutRecommender`（新規）でカード 1 件ずつプロンプトを生成し、工程3 で使用している Orchestrator のポリシーを再利用して推奨レイアウトを取得する。
   - プロンプトにはカード本文、意図タグ、章テンプレ要件、利用可能なテンプレ一覧（用途タグと主要アンカー情報）を含める。
   - 推薦結果は `layout_candidates[]`（`layout_id`, `score`, `reasons[]`）として保持する。AI 応答が得られない場合はヒューリスティック（用途タグ一致、容量適合度、章配列バランス）で補完する。
5. **カード→スライド割当**:
   - `jobspec.slides` に未使用スライドがある限り、カード候補のうち `layout_id` が一致するものを選定する。
   - 同一レイアウトが複数カードに割り当たる場合は章テンプレの `required_sections` / `min_slides` 条件を考慮し、付録送り候補を決定する。
   - 割当結果は `DraftSlideAllocation`（内部モデル）として保持し、HITL 操作用に `ref_id`（card_id）と `layout_hint`（jobspec.layout）を記録する。
6. **承認フロー**:
   - CLI で章・スライド単位の承認／差戻し／付録送りを操作すると、`draft_review_log.json` に履歴を記録し、`generate_ready_meta.sections[*].status` を更新する。
   - 差戻し時には `return_reasons.json` からコードを選択し、カードに紐付ける。差戻し後にカードが再割当されると過去ログはバージョンとして保持する。
7. **generate_ready 出力**:
   - 割当済みスライドを `GenerateReadySlide` へ変換する。`elements` にはカードの `message`, `narrative`, `supporting_points` をアンカー構造に合わせて整形して格納。
   - `meta.sources` には `card_id` を記載し、工程5 以降でトレース可能にする。
   - `generate_ready_meta.json` へは章テンプレ適合率、AI 推薦件数、差戻し統計、Analyzer 指摘要約（severity 別件数）を記録する。

## 主要コンポーネント
| コンポーネント | 役割 | 備考 |
| --- | --- | --- |
| `BriefNormalizationStep` | Brief 成果物の読み込み。`PipelineContext` に `brief_document` を格納し、互換の `content_approved` を生成（工程5 互換用途）。 | RM-047 では `content_approved` 互換出力を段階的に縮退させる。 |
| `CardLayoutRecommender`（新規） | カード単位でテンプレ候補をスコアリング。AI 推薦＋ヒューリスティックのハイブリッド。 | 生成AIの利用有無は設定で切り替え可能。 |
| `DraftStructuringStep`（刷新） | `brief_document` と `jobspec` を突合し、`DraftAllocationResult` を生成。章テンプレ適合、付録候補判定を実施。 | 出力は `generate_ready` 専用アーティファクトへ転送。 |
| `GenerateReadyBuilder`（新規） | 割当結果から `GenerateReadyDocument` とメタ情報を構築。 | CLI から直接利用。 |
| `draft_review_log.json` | HITL 操作ログ。`action` は `approve`/`return`/`appendix`/`hint` 等。 | Approval-First Policy と整合する。 |

## データモデル要約

### GenerateReadyDocument
```jsonc
{
  "slides": [
    {
      "layout_id": "Right Highlight Detail",
      "elements": {
        "title": "カードの主要メッセージ",
        "subtitle": "章名など",
        "body": ["narrative を最大 5 行"] ,
        "supporting_left": ["支援ポイント"],
        "supporting_right": ["支援ポイント"],
        "evidence_table": {
          "headers": ["指標", "値"],
          "rows": [["KPI", "+15%"], ["CS", "4.6"]]
        }
      },
      "meta": {
        "section": "INTRO",
        "page_no": 1,
        "sources": ["intro"],
        "fallback": "none"
      }
    }
  ],
  "meta": {
    "template_version": "v2025.11",
    "template_path": "templates/corporate_v2025.pptx",
    "generated_at": "2025-11-04T08:00:00Z",
    "job_meta": { "title": "案件名" },
    "job_auth": { "created_by": "operator" }
  }
}
```

### draft_review_log.json （抜粋）
```jsonc
[
  {
    "target_type": "slide",
    "target_id": "intro",
    "action": "approve",
    "actor": "operator-a",
    "timestamp": "2025-11-04T08:10:00Z"
  },
  {
    "target_type": "slide",
    "target_id": "impact",
    "action": "return",
    "actor": "operator-b",
    "timestamp": "2025-11-04T08:12:00Z",
    "changes": {
      "return_reason_code": "LAYOUT_CAPACITY",
      "notes": "文章量が多いため 2 カラムへ振り分ける"
    }
  }
]
```

### generate_ready_meta.json（例）
```jsonc
{
  "sections": [
    {
      "id": "intro",
      "title": "イントロダクション",
      "status": "approved",
      "slides": [
        {
          "card_id": "intro",
          "layout_id": "Agenda",
          "ai_recommended": true,
          "analyzer_summary": {
            "severity_high": 0,
            "severity_medium": 1
          }
        }
      ]
    }
  ],
  "template": {
    "chapter_template_id": "base_4step",
    "match_score": 0.92,
    "mismatch": []
  },
  "statistics": {
    "cards_total": 12,
    "approved_slides": 12,
    "appendix_slides": 1,
    "ai_recommendation_used": 10
  }
}
```

## CLI / API 更新点
- `uv run pptx outline` / `pptx compose` は `generate_ready.json` / `generate_ready_meta.json` を既定名で出力し、MappingStep 側でも同名で成果物を揃える。
- `mapping_log.json` / `fallback_report.json` は既定名で出力し、フォールバックが発生した場合にのみレポートを生成する。
- 従来の `--draft-filename` / `--approved-filename` / `--meta-filename` は後方互換のため継続し、CLI 実行後は Draft 系と Ready 系の生成物パスが両方表示される。
- `pptx mapping` も同じ命名オプションを受け取り、工程5 が参照する `generate_ready` / `mapping_log.json` を統一出力する。
- API 側のドラフト関連エンドポイントは `generate_ready` を第一級成果物として扱い、工程5 での参照を `generate_ready` 系に一本化する。

## 未決事項とリスク
- AI 推薦のプロンプト詳細とモデル選定。工程3 で使用しているローカル LLM スタブを流用し、将来的な API 連携に備えた抽象化が必要。
- `jobspec.json` に含まれないテンプレ専用メタ（例: 配色テンプレ ID、動的エレメント定義）が必要になった場合の拡張方法。工程2 の抽出結果で補完できるか確認が必要。
- `generate_ready_meta.json` の粒度（差戻しログとの重複）。運用側の監査要件と整合するよう調整する。

## 実装ステップ（次工程）
1. モデル追加 (`GenerateReady*`, `DraftAllocationResult` など) とユーティリティ実装。
2. `pipeline/draft_structuring.py` の刷新と `GenerateReadyBuilder` の追加。
3. CLI コマンド（`outline`）の引数・出力更新、市場テストサンプルの整備。
4. テスト更新（ユニット・統合）と CLI 実行確認。
5. ドキュメント追従（README, runbook 等）。

以上の設計内容について、実装着手前にレビューとフィードバックを依頼する。
