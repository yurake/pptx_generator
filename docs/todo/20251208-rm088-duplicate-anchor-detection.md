---
目的: RM-088 テンプレ抽出でアンカー名重複を検出してエラー化する
関連ブランチ: feat/rm088-duplicate-anchor-detection
関連Issue: #412
roadmap_item: RM-088 テンプレ実スライド優先抽出
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ copilot/detect-duplicate-anchor-names が既に存在し、作業ツリーがクリーンであることを確認。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記完了（承認メッセージ ID: 3626256335）
    - 対象整理: テンプレート抽出時に同一スライド内でアンカー名の重複を検出し、エラー化する
    - 対象ファイル: src/pptx_generator/pipeline/template_extractor.py、tests/template_audit/test_template_extractor_jobspec_output.py
    - 修正方針: _extract_layout_info メソッド内で _check_duplicate_anchors メソッドを呼び出し、重複を検出したら RuntimeError を投げる
    - リスク: 既存テンプレートに重複アンカー名が存在する場合、抽出が失敗する
    - テスト方針: 重複検出、異なるスライド間の同名アンカーは許容、unnamed 図形の除外を確認
    - 承認メッセージ ID: 3626256335
- [x] 設計・実装方針の確定
  - メモ: Plan 承認内容に基づき実装方針を確定
    - _check_duplicate_anchors メソッドを追加し、アンカー名の重複をチェック
    - 重複が見つかった場合は詳細なエラーメッセージを含む RuntimeError を投げる
    - unnamed で始まる図形名は自動生成名として重複チェックから除外
- [x] 実装
  - メモ: template_extractor.py に _check_duplicate_anchors メソッドを実装
    - 同一スライド内でのアンカー名重複を検出
    - エラーメッセージには重複アンカー名、スライド情報、修正方法を含める
    - RuntimeError を投げて処理を中断（extract_template_spec の例外ハンドリングで即座に伝播）
- [x] テスト・検証
  - メモ: 3 つのテストケースを追加し、すべて合格
    - test_duplicate_anchor_detection_in_same_slide: 同一スライド内の重複検出
    - test_no_duplicate_anchor_different_slides: 異なるスライド間での同名アンカーは許容
    - test_unnamed_shapes_ignored_in_duplicate_check: unnamed 図形は除外
    - 実行結果: 17 passed（新規 3 件 + 既存 14 件）
- [ ] ドキュメント更新
  - メモ: 機能追加のため実装詳細を確認後、必要に応じて更新
  - [x] docs/roadmap 配下
    - メモ: RM-088 は既に完了済みとマークされており、本機能は品質向上のための追加実装のため更新不要
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: テンプレ抽出の要件は既存ドキュメントでカバーされており、重複検出は品質チェックの強化のため更新不要
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計ドキュメントは Stage1 の全体フローを記載しており、詳細な実装ロジックは含まないため更新不要
  - [x] docs/runbook 配下
    - メモ: 運用手順書には影響なし。エラーが発生した場合の対処は既にエラーメッセージ内で案内されているため更新不要
  - [x] README.md / AGENTS.md
    - メモ: ユーザー向け機能説明は変更なく、内部品質向上のため更新不要
- [x] 関連Issue 行の更新
  - メモ: 関連Issue が特定できたら更新
- [ ] チェックリスト整合確認
  - メモ: 親タスク完了確認
- [ ] PR 作成
  - メモ: PR 番号と URL を記録

## メモ
- 背景: RM-088 の静的テンプレ検証で、同一スライド内で同じアンカー名 `テキスト プレースホルダー 2` が 2 つ存在し、Stage3 ドラフト構築で上書きされる不具合が発生
- ゴール: テンプレート抽出時にスライドごとのアンカー名重複を検出し、分かりやすいエラーメッセージで処理を中断する
- 実装完了日時: 2025-12-08
- 実装概要:
  - `_check_duplicate_anchors` メソッドを追加し、同一スライド内のアンカー名重複を検出
  - 重複検出時は詳細なエラーメッセージ（アンカー名、スライド情報、修正方法）を含む RuntimeError を投げる
  - 異なるスライド間での同名アンカーは許容（問題なし）
  - unnamed で始まる図形名は自動生成名として重複チェックから除外
