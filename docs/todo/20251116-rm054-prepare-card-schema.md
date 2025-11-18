---
目的: prepare_card.json のスキーマをゼロベースで再設計し、後続工程が扱いやすい構造へ刷新する
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: #272
roadmap_item: RM-054 静的テンプレ構成統合
---

- [ ] ブランチ作成と初期コミット
  - メモ: 既存ブランチ feat/rm054-static-blueprint-plan 上で継続作業
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan（2025-11-16）
    - 対象整理（スコープ、対象ファイル、前提）: prepare_card.json の構造そのものを見直し、テンプレート非依存なスライド下書きとして再定義する。関連する読み込み処理（PrepareNormalizationStepなど）とサンプルも整合させる。
    - ドキュメント／コード修正方針: スキーマ案に沿って `src/pptx_generator/prepare` と `pipeline/prepare_normalization.py`、および `samples/prepare/*.json` を刷新し、仕様ドキュメント（requirements/design）を更新する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo で進捗管理し、スキーマ案・実装結果をユーザーと擦り合わせる。
    - 想定影響ファイル: `src/pptx_generator/prepare/*.py`, `src/pptx_generator/pipeline/prepare_normalization.py`, `tests/test_cli_prepare.py`, `samples/prepare/*.json`, `docs/requirements/stages/stage-02-content-normalization.md`, `docs/design/schema/stage-02-content-normalization.md`。
    - リスク: compose/mapping 等の後段工程が旧スキーマを前提としており、合わせて修正する必要がある。移行期間中の互換性は担保しない。
    - テスト方針: CLI prepare のモック／Azure 実行、関連 pytest を更新して実行する。
    - ロールバック方法: 新スキーマに起因する問題があれば該当変更を元に戻し、旧スキーマへ復元する。
    - 承認メッセージ ID／リンク: ユーザー承認 (「ok, 新規にtodoを作成して対応しよう」)
- [x] 設計・実装方針の確定
  - メモ: 新スキーマ（role/content/meta）を前提としたコード・テスト刷新方針を決定し、パイプライン／API／CLI の影響範囲を整理済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: stage-02 schema / requirements と関連ノートを新フィールド構成へ更新。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: ドメイン層〜CLI まで新スキーマへリファクタリングし、API ストアとパイプライン互換層を更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_cli_outline.py tests/test_mapping_step.py tests/test_slide_alignment.py tests/test_analyzer.py` を実行し、主要ケースの回帰確認済み。
- [ ] ドキュメント更新
  - メモ:
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ:
- [ ] PR 作成
  - メモ:

## メモ
- 2025-11-16: ユーザーと `prepare_card.json` の目的と必須要素をゼロベースで擦り合わせ。以下のような確認事項・方針を共有。
  - 目的: テンプレート非依存のスライド下書きを記録し、compose 以降が柔軟に扱える構造へ刷新する。
  - 必須要素の洗い出し: 1) 識別子（card_id, order）、2) 役割情報（story_phase, intent_tags）、3) コンテンツ本体（title, headline, body, notes）、4) 必要に応じたメタ情報。
  - card_id: 連番のみだと差分追跡が困難になるため、意味のあるスラグ（phase＋short slug など）＋独立した `order` を持つ構成が望ましい。再生成時に ID が安定することを重視。
  - headline: 「単なる要約」ではなく、「そのページで最も伝えたい結論」を短く明示する項目として扱う。コメントで意図を明文化。
  - body: `type` 付きブロックの配列。段落・箇条書き・表・メディアなど柔軟に記述できるようにし、必要に応じて `type: "agenda"` や `type: "executive_summary"` のようなカスタムタイプを追加してよい。本文が不要なスライド（タイトルだけ等）は空配列でもよい。
  - notes: PowerPoint のノート欄に転記する前提で、生成 AI が本文の意図や補足説明、根拠（旧 supporting）を書き込む場所にする。閲覧者に提示するかは利用者が判断する。
  - supporting: notes に統合する方針とし、別フィールドとしては持たない。旧スキーマの `supporting_points` は notes に変換する。
  - HITL 情報（status, autofix）は `prepare_log.json` など別ファイルで管理。`prepare_card.json` には含めない。
  - 特殊ページ（タイトルのみ、アジェンダのみなど）は body を空配列にしたり特定の block type を使うことで表現する。これをドキュメントにも明記。
- 2025-11-16: ドキュメント（requirements/design schema）を新スキーマ前提に書き換え。後方互換の記述は不要との方針に従い、新しい構造を「現行仕様」として記載。特殊スライドの表現方法（body 空配列許容、独自 block type を追加可）も明記済み。ただし実装はこれから。
- 2025-11-16: 今後の実装方針に関するメモ。
- `prepare/models.py` で `PrepareCard` を `role` / `content` ベースに再定義し、旧フィールド（chapter, message, narrative, supporting_points, status 等）を廃止する。HITL 関連の型（PrepareStatusType, PrepareEvidence 等）も用途が無くなるため整理する。
  - `PrepareAIOrchestrator` を新スキーマ向けに刷新し、LLM から `title` / `headline` / `body` / `notes` を受け取る。旧 `supporting_points` を notes へ変換する互換レイヤーを設ける。
  - プロンプト側で「notes はノート欄に記載する補足情報」「headline はページの結論」といった指示を入れ直す。
  - `PrepareNormalizationStep` で `PrepareCard` の新構造を取り込み、後段の `ContentSlide` へ変換する処理も更新する。`body` ブロックや notes を適切に PPT 要素へマッピングする必要がある。
  - `samples/prepare/*.json` を新構造で再生成し、`tests/test_cli_prepare.py` や `tests/test_draft_structuring_step.py` 等に反映する。
  - compose / mapping など後工程は旧構造前提なので、実装後は順次そちらも改修する。移行期間に互換レイヤーを設ける想定はなし（後方互換は考えない方針）。
  - CLI prepare や Azure 実行の動作確認 (`uv run pptx prepare ...`) を mock / 実環境双方で再確認する。`widgets` 等の追加ブロックにも対応可能なよう、body のバリデーションは緩めにする。
- 次の担当者への TODO 例:
1. `prepare/models.py` で新スキーマの型（PrepareCardRole, PrepareCardContent, PrepareBodyBlock, PrepareNoteEntry 等）を実装し、関連箇所を更新する。
2. `prepare/orchestrator.py` で LLM 出力を新型へ変換するロジックを整備。`notes` へのマッピング、`card_id` の slug 化、`order` の割当などを実装。
  3. プロンプトを更新し、LLM に headline/body/notes 役割を説明する。
  4. `pipeline/prepare_normalization.py` → ContentSlide 変換を新構造に合わせて改修。テーブルやメディアをどう扱うか決める。
  5. サンプル／テスト更新 (`samples/prepare/*.json`, CLI テスト, draft_structuring テストなど)。
  6. 後段（compose/mapping/gen）のコードを順次新スキーマに合わせる。`content.body` の情報を generate_ready へどう流し込むか設計が必要。
  7. Azure 実行での再確認。`notes` をノート欄へ入れるロジックが compose 側に必要なら追対応。
