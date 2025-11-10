---
目的: usage_tags の抽出を生成AIベースへ移行し、テンプレ抽出段階でのタグ品質を統制する
関連ブランチ: feat/rm061-usage-tags-governance
関連Issue: #281
roadmap_item: RM-061 usage_tags ガバナンス強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-09 `main` から `feat/rm061-usage-tags-governance` を作成し、本 ToDo を追加する初期コミット（`docs(todo): bootstrap rm061 usage tags governance ai extraction`）を実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: テンプレ抽出ステップ（`TemplateExtractor`／`layout_validation`）を中心に、Stage1 で `usage_tags` を生成 AI に置き換える。既存 `usage_tags` ヒューリスティックはフォールバックとして残し、Stage3 以降の呼び出しには影響させない。
    - ドキュメント／コード修正方針: `template_ai` モジュールを新設し、テンプレ抽出中にレイアウト情報を AI へ渡してタグを受け取る。`layout_validation` で AI 由来タグとフォールバックを記録し、`diagnostics` に統計を出力する。CLI からの設定・ログ出力・ドキュメント（`docs/notes/20251109-usage-tags-scoring.md` 等）を更新する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 各工程完了後に ToDo を更新し、最終的に PR で差分・ログ出力・検証結果を共有。必要に応じて `docs/notes` に検討事項を追記する。
    - 想定影響ファイル: `src/pptx_generator/pipeline/template_extractor.py`, `src/pptx_generator/layout_validation/suite.py`, 新規 `src/pptx_generator/template_ai/*`, CLI 設定（`src/pptx_generator/cli/template.py` など）、`docs/notes/20251109-usage-tags-scoring.md`, テスト類。
    - リスク: AI 応答フォーマット揺らぎやタイムアウトによる抽出失敗、API 呼び出しコスト増、既存テンプレとの差異で Stage3 以降のスコアリングが変わる可能性。フォールバックと詳細ログで影響を可視化し、設定で OFF にできるようにする。
    - テスト方針: 新規ユーティリティのユニットテスト、テンプレ抽出フローのモック検証、`uv run pptx tpl-extract` を用いた手動確認。必要に応じて `tests/test_template_extraction_*.py` を追加。
    - ロールバック方法: `feat/rm061-usage-tags-governance` のコミットをリバートし、AI 呼び出しを無効化して既存ヒューリスティックへ戻す。
    - 承認メッセージ ID／リンク: チャットログ（2025-11-09 Plan 承認）
- [x] 設計・実装方針の確定
  - メモ: テンプレ抽出で AI 推定を主としつつヒューリスティックをフォールバックに回す構成とし、`template_ai` 新設・CLI 連携・診断拡張までをスコープとする方針を確定。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [x] 実装
  - メモ: `template_ai` モジュールを追加し、`layout_validation` で AI 推定を採用。CLI オプション／診断統計の拡張、フォールバックおよび警告ロジックを実装。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_template_ai.py tests/test_layout_validation_template_ai.py tests/test_layout_validation_usage_tags.py` を実行し、AI 推定とフォールバックの挙動を確認。
- [x] ドキュメント更新
  - メモ: `docs/notes/20251109-usage-tags-scoring.md` に Stage1 AI 推定の流れと CLI オプションを追記。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

- [ ] layout_ai policy への影響確認
  - メモ: Stage3 で利用する layout_ai policy との整合性、タグ語彙の差異有無を確認する。
- [ ] Stage3 スコアリング差異の評価
  - メモ: AI 由来タグが Stage3 推薦に与える影響を検証し、必要な調整があれば別 ToDo / PR へ切り出す。
- [x] CLI 統合テストの追加
  - メモ: `scripts/test_template_ai.sh` と `tests/test_template_ai_script.py` で `uv run pptx tpl-extract` のモックポリシー検証を追加。
- [ ] README / AGENTS / roadmap 更新
  - メモ: CLI オプション追加とテンプレ AI 設定例を各ドキュメントへ反映する。
- [ ] 用途タグ体系の再設計（Plan）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: Canonical usage tags を「Intent（章区切り・クロージング等）」と「Media（chart/table/visual）」の2軸で再定義し、`utils/usage_tags.py`・テンプレ AI・layout_ai スコアリングの語彙を統一する。テンプレ抽出／Stage3 双方で新語彙に対応する改修を行う。
    - ドキュメント／コード修正方針: Canonical セットとシノニムを拡張し、`CardLayoutRecommender`・`mapping` の加点ロジックを更新。テンプレ AI ポリシー／プロンプトを新語彙へ差し替え、診断・ログの出力内容も調整する。必要に応じて Stage3 スコアリング設計資料を更新。
    - 確認・共有方法: ToDo を段階更新し、設計変更は `docs/design` / `docs/requirements` に反映。PR で差分説明と影響まとめを共有。
    - 想定影響ファイル: `src/pptx_generator/utils/usage_tags.py`, `src/pptx_generator/template_ai/*`, `src/pptx_generator/draft_recommender.py`, `src/pptx_generator/pipeline/mapping.py`, `config/template_ai_policies.json`, 関連ドキュメント。
    - リスク: 語彙変更による Stage3 推薦結果の変動、既存テンプレートとの互換性、AI プロンプトの再チューニング。段階的にフィードバックを取りながら調整する。
    - テスト方針: ユニットテストで新 Canonical タグの正規化・加点ロジックを検証し、テンプレ抽出・Stage3 推薦の統合テストを追加。代表テンプレートで `uv run pptx template` と `uv run pptx compose` を実行し、生成物の差異を確認する。
    - ロールバック方法: 新語彙関連のコミットをリバートし、旧 Canonical セットとテンプレ AI ポリシーへ戻す。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
