---
目的: RM-086 静的テンプレート抽出の静的文言保持方式検討
関連ブランチ: docs/rm086-static-hooks-prep
関連Issue: 未作成
roadmap_item: RM-086 静的テンプレ外部フック統合
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 参照済みドキュメント: docs/policies/context-engineering.md, CONTRIBUTING.md, docs/policies/task-management.md, temp/handover-rm086-20251206.md, docs/todo/20251206-rm086-template-spec-static-text.md, docs/notes/20251204-rm086-static-hooks.md, .pptx/jri/extract/template_spec.json, src/pptx_generator/pipeline/template_extractor.py, src/pptx_generator/models/template.py, src/pptx_generator/pipeline/draft_structuring/step.py, external/経費投資/stage04_gen.py
    - Scope / 対象  
      - Stage1 抽出ロジック（`src/pptx_generator/template_extractor/`）で静的テキスト要素を Blueprint/JSON へ保持する仕様検討  
      - Stage4 レンダリング（`src/pptx_generator/pipeline/renderer/` 及び静的モード用外部フック）で JSON の静的文言を再利用する方式の設計整理  
      - Blueprint / `template_spec.json` スキーマと関連ドキュメントの更新方針策定  
    - 想定影響ファイル  
      - `src/pptx_generator/template_extractor/*`  
      - `src/pptx_generator/pipeline/renderer/*` と静的モード連携部  
      - `docs/design/stages/stage-01-template.md`, `docs/design/stages/stage-04-gen.md` など設計系資料  
      - Blueprint 生成物 (`template_spec.json`, `generate_ready.json`)  
    - リスク / 懸念  
      - Blueprint サイズ増加による抽出時間・I/O オーバーヘッド  
      - 既存静的外部フックとの仕様不整合  
      - テキスト/表が複合するスライドでのアンカー重複処理  
    - テスト方針（実装時）  
      - `uv run pptx template`→`uv run pptx generate` の静的モード通し確認  
      - Stage1/Stage4 ユニットテストで静的文言の保持・復元を検証  
      - 既存差分比較スクリプト（`scripts/inspect_static_pptx.py` など）を用いた結果検証  
    - ロールバック  
      - Stage1/Stage4 の変更を revert し、現行の静的フック頼りの復元方式へ戻す  
      - Blueprint から静的テキスト追加分を削除し、従来スキーマへ復旧
    - 対象整理（スコープ、対象ファイル、前提）: Stage1 (template) 抽出で静的 placeholder 文言も JSON に含め、Stage4 では JSON を参照して静的文言を復元する方針を整理。既存の Stage4 フック暫定対応は撤回し、標準パイプラインで完結させる。`
    - ドキュメント／コード修正方針: `src/pptx_generator/template_extractor/*`, Blueprint スキーマ、Stage4 renderer、外部フック差分の整理、および docs 更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo を更新し、必要に応じて docs/notes/20251204-rm086-static-hooks.md に記録。レビューは PR で実施。
    - 想定影響ファイル: `src/pptx_generator/template_extractor`, `src/pptx_generator/pipeline/draft_structuring`, `src/pptx_generator/pipeline/renderer`, Stage4 外部フック、`template_spec.json` スキーマ、関連テスト。
    - リスク: JSON サイズ増加による性能影響、既存テンプレ抽出との互換、外部フックとの整合、テスト更新コスト。
    - テスト方針: 抽出→生成の通しテスト (`uv run pptx template` 〜 `gen`)、ユニットテストで静的文言が保持されること、差分比較スクリプトで検証。
    - ロールバック方法: Stage1/Stage4 の変更を revert し、静的文言をコード内で復元する従来方式に戻す。
    - 承認メッセージ ID／リンク: （承認取得後に更新）
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: TemplateBlueprintSlot に default_text/default_payload を追加し、Stage1 で静的テキストを保持、Stage3 で未割当 slot に既定値を適用、Stage4 Renderer にアンカー正規化・レイアウト図形複製を追加。Stage4 外部フックは hooks.json から除外済み。
- [x] テスト・検証
  - メモ: `uv run pptx template --layout-mode static templates/経費投資.pptx` → `prepare` → `mapping` → `gen` を通し、外部 Stage4 フックなしで PPTX 生成が成功することを確認。slot13 カードを一時的に削除して mapping を再実行し、`default_applied: true` が `mapping_log.json` に出力され `generate_ready` に Blueprint 既定値が挿入されることを確認（検証後は原状復帰）。
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- Blueprint モデル拡張仕様
  - TemplateBlueprintSlot（src/pptx_generator/models/template.py:60）へ以下フィールドを追加する想定で仕様
    を確定。
      - default_text: list[str] | None = None … プレーンテキスト要素の既定行を保持。
      - default_payload: dict[str, Any] | None = None … 表・図・チャートなど構造化要素用の任意ペイロー
        ド。
  - JSON 後方互換性: 既存 Blueprint 出力に影響を与えないよう両フィールドは None デフォルト。
    template_spec.json の schema を追従更新（docs 側で告知）し、旧ファイルも読み込み可能。
  - TemplateBlueprintSlide/TemplateBlueprint は変更不要。TemplateSpec にも影響なし。

  Stage1 (template_extractor) での静的テキスト取り込み方針

  - 変更ファイル: src/pptx_generator/pipeline/template_extractor.py。
  - _build_blueprint (同:682) 内で TemplateBlueprintSlot 生成直前に ShapeInfo.text を判定。
      - content_type == "text" の場合、anchor.text を strip() → 改行で分割し default_text へ設定（空行は
        除外）。
      - その他の要素は当面 None。将来的に表系が必要なら default_payload をスケルトンで作成できるように
        する。
  - 併せて ShapeInfo.text が空／テンプレ auto-draw などのケースでは何もしない。
  - 出力 template_spec.json に default_text が埋め込まれることを確認（.pptx/jri/extract/
    template_spec.json で差分テスト）。

  - 変更ファイル: src/pptx_generator/pipeline/draft_structuring/step.py。
  - _build_static_artifacts の slot ループ（同:1006）でカード不在時に Blueprint 既定値を利用。
      - slot.default_text が存在すれば elements[slot.anchor] = slot.default_text。
      - slot.default_payload が dict ならそのまま格納。
  - MappingSlideMeta (mapping_log 用) に default_applied フラグ追加案: slot_records に default_applied:
    bool を加え、ログで可視化。
  - slot_summary や unused_slots 算出ロジックは従来通り（未充足扱い）。Blueprint 既定値で埋めた場合
    も fulfilled=False のままにし、静的コンテンツがカード経由で提供されていないことが一目で分かるように
    する。

  Stage4／外部フック整理とテスト

  - Renderer (src/pptx_generator/pipeline/renderer.py) は generate_ready.elements をそのまま使うため、
    Stage3 のフォールバックで静的文言が流れ込めば外部フック不要。
  - 移行手順:
      1. 静的 Blueprint から生成された generate_ready.json を検証し、STATIC_TEXT_ANCHORS の値が存在するこ
         とを確認。
      2. external/経費投資/stage04_gen.py の静的テキスト差し込みを撤廃 → hooks.json の gen エントリを
         null に戻す。
      3. テスト: uv run pptx template --layout-mode static, prepare, mapping, gen を通し .pptx/jri/
         mapping/generate_ready.json → .pptx/jri/gen/*.pptx の整合を scripts/inspect_static_pptx.py で
         確認。
      4. ドキュメント更新: docs/design/stages/stage-01-template.md と stage-04-gen.md に Blueprint デフォ
         ルトとフック縮小方針を追記。
  - 12/06 更新: 上記設計を反映し Stage1/Stage4 ドキュメントへ Blueprint 既定値とレンダラ改修の追記を実施。
