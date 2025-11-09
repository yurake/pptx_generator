---
目的: 工程4でブリーフとテンプレ spec を統合し `draft_approved.json` の生成基盤を整備する
関連ブランチ: feat/rm047-draft-structuring
関連Issue: #264
roadmap_item: RM-047 テンプレ統合構成生成AI連携
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm047-draft-structuring を main から作成し、ToDo 追加を初期コミットとして作成。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
      1. **前提調査と要件整理**  
         - `docs/requirements/stages/stage-04-draft-structuring.md`、`docs/design/design.md`、`docs/notes/20251102-stage2-jobspec-overview.md` を読み合わせ、工程2 出力（`jobspec.json`）と工程3 出力（`brief_cards.json` など）の項目を洗い出す。  
         - `feat/rm049-pptx-gen-scope` ブランチの Stage5 実装（`generate_ready.json` など）を確認し、工程4で追加すべきフィールドやメタ情報を整理する。工程2 由来で `jobspec.json` 以外の参照が必要と判明した場合は ToDo / docs/notes で報告する。  
      2. **設計ドキュメントの整備**  
         - `docs/design/draft-structuring-RM047.md`（新規）を作成し、カード単位 AI マッピングのフロー、AI 呼び出しインターフェース（工程3 資産との連携）、`generate_ready.json`／承認ログ／メタ情報の構成を詳細化する。  
         - `docs/design/design.md` と `docs/requirements/stages/stage-04-draft-structuring.md` に要点を反映し、工程4 の入出力・品質ゲートを `generate_ready` ベースへ更新する。  
         - `docs/roadmap/roadmap.md` の RM-047 セクションを進行中へ更新し、新設ドキュメントへのリンクを追加する。  
      3. **モデル・ユーティリティ追加**  
         - `src/pptx_generator/models.py` に `GenerateReadyDocument` 系モデルを追加し、旧 `Draft*`/`RenderingReady` 系に依存しない構造へ刷新する。  
         - `src/pptx_generator/generate_ready.py` を新規実装し、`generate_ready_to_jobspec` など Stage5 で必要な変換ユーティリティを提供する。  
      4. **工程4 パイプライン実装**  
         - `pipeline/draft_structuring.py` を `brief_cards.json` と `jobspec.json` の突合前提に書き換え、カード単位の割当結果を `GenerateReadyDocument` へ連携できるようにする。  
         - `pipeline/brief_normalization.py`・`pipeline/mapping.py` を含む CLI パイプラインを全面刷新し、`draft_*`／`rendering_ready` 出力を廃止。`generate_ready.json` を唯一の後続入力として扱う。  
         - `src/pptx_generator/cli.py` の `pptx outline` コマンドを新仕様に対応させ、不要オプションを廃止しつつ `generate_ready` 出力と承認ログ・メタファイルを生成する。  
      5. **生成AIマッピング補助の実装**  
         - [x] BriefCard を 1 枚ずつ評価するマッピング補助ロジック（AI 推薦＋ヒューリスティック）を実装し、推奨結果を `DraftLayoutCandidate` 相当のスコアに反映。CardLayoutRecommender を追加し、`layout_score_detail.ai_recommendation` を出力。  
         - [x] 生成AIのプロンプト設計を工程3 の実装を参考に整理し、コード上の拡張ポイントとして組み込む。AI weight と最大候補数をオプション化し、`config/layout_ai_policies.json` を通じて LLM 接続（Mock / OpenAI）を切り替えられる構造を整備。`draft_mapping_log.json` へ model / reasons を含む応答を記録。  
      6. **テストの更新・追加**  
         - [x] `tests/test_draft_structuring_step.py` などモデル／ユーティリティ単位のテストを `generate_ready` ベースへ更新し、新旧出力の差異を検証する。AI スコアの存在チェックを追加。  
         - [x] 生成AI補助向けのユニットテストを追加してカード割当結果を検証。`tests/test_layout_recommender.py` で LLM モック応答とフォールバック挙動を確認。  
      7. **テスト実行と検証**  
         - `uv run --extra dev pytest` を実行し、主要テストの成功を確認する。必要に応じて `ruff`・`black --check`・`mypy` を適用する。  
      8. **フォローアップ**  
         - 工程2 から追加で必要となった情報があれば docs/notes と ToDo メモに記録し、ユーザーへ報告する。  
      - スコープ: 工程4 全体を `generate_ready` 基盤へ全面置換し、既存 `draft_*` および `rendering_ready` 系の入出力は廃止する。後方互換の考慮は不要、完全新規置換で進める。  
      - 想定影響ファイル: `docs/design/draft-structuring-RM047.md`（新規）、`docs/design/design.md`、`docs/requirements/stages/stage-04-draft-structuring.md`、`docs/roadmap/roadmap.md`、`src/pptx_generator/models.py`、`src/pptx_generator/cli.py`、`src/pptx_generator/generate_ready.py`（新規）、`src/pptx_generator/pipeline/brief_normalization.py`、`src/pptx_generator/pipeline/draft_structuring.py`、`src/pptx_generator/pipeline/mapping.py`、該当テストファイル。  
      - リスク: BriefCard 仕様変更の波及、AI 推薦精度の不確実性による再調整、CLI 引数廃止に伴うドキュメント更新漏れ。  
      - テスト方針: 上記テスト更新に加え、`uv run --extra dev pytest` を実行して全体整合を確認する。  
      - ロールバック方法: 変更・追加した Markdown および Python ファイルを個別に戻すことで復旧可能。  
      - 承認メッセージ: ユーザー発言「ではtodoに計画を転記し、作業に取り掛かってください。」（2025-11-04）。
- [x] 設計・実装方針の確定
  - メモ: `generate_ready` 基盤への移行設計はユーザー承認済み（2025-11-04）。関連ドキュメントは `docs/design/stages/stage-03-mapping.md`、`docs/design/design.md`、`docs/requirements/stages/stage-04-draft-structuring.md` で整合を確認済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: Stage3/4 関連ドキュメントを `generate_ready` 基盤へ更新済み（commit `edfabde`）。追加の設計補足は今後の実装ブランチで反映予定。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `DraftStructuringStep` で `generate_ready.json` / `generate_ready_meta.json` を生成。`pptx outline` / `compose` / `mapping` に generate_ready 系オプションを追加し、`MappingStep` でも `generate_ready_meta.json` を出力先へ複製するよう調整済み。
- [x] テスト・検証
  - メモ: 個別テストに加えて `uv run --extra dev pytest` を実行し、全体の回帰を確認済み。
- [ ] ドキュメント更新
  - メモ: README と `docs/design/cli-command-reference.md`、`docs/design/stages/stage-03-mapping.md`、`docs/requirements/stages/stage-03-mapping.md` を更新し、`mapping_log.json` へのリネームと CLI 新オプションを反映済み。runbook の運用手順も追随。
  - [ ] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 未特定のため要確認
- [x] PR 作成
  - メモ: PR #282 https://github.com/yurake/pptx_generator/pull/282（2025-11-09 完了）

## メモ
---
承認メッセージ: ユーザー「ok」（本対話）。
計画メモ: Legacy brief オプションの完全削除とテンプレートパスの相対化対応を実施する。
