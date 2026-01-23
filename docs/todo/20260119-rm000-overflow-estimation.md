---
目標: 事前推定の精度を改善し、溢れ予測の誤差を縮める
関連ブランチ: feat/overflow-estimation
関連Issue: #540
roadmap_item: RM-000 例: RMなしIssue B
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名: feat/overflow-estimation / 初期コミット: docs(todo): add rm000 overflow estimation / push: 済み
    - 必ず main からブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること
    - 対象スコープ: text_capacity の推定に段落間隔とインデント補正を反映
    - 対象ファイル: src/pptx_generator/utils/text_capacity.py, tests/utils/test_text_capacity.py
    - 前提: paragraph は先頭段落の情報を使う
    - ドキュメント／コード修正方針: 推定ロジック更新とユニットテスト追加
    - 確認・共有方法: ToDo 更新、テスト結果の記録
    - 想定影響ファイル: layout_validation の max_lines 推定値
    - リスク: max_lines 推定の変化でレイアウト選定が変わる可能性
    - テスト方針: python -m pytest tests/utils/test_text_capacity.py
    - ロールバック方針: 変更箇所を revert
    - 承認メッセージ ID／リンク: ユーザー OK
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針を記載し、ユーザー確認が必要な論点があれば列挙する
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: src/pptx_generator/utils/text_capacity.py, tests/utils/test_text_capacity.py
- [x] テスト・検証
  - メモ: PYTHONPATH=src python -m pytest tests/utils/test_text_capacity.py / 5 passed / coverage.xml / diff-cover: python -m diff_cover.diff_cover_tool coverage.xml --compare-branch origin/main / Coverage 100%（11 lines）
- [x] ドキュメント更新
  - メモ: docs/todo/20260119-rm000-overflow-estimation.md, C:\PPT_test_textyabai\実施事項概要.md
  - メモ: 対象外: docs/roadmap 配下, docs/requirements 配下, docs/design 配下, docs/runbook 配下, README.md / AGENTS.md
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合を確認）
  - [x] docs/design 配下（実装結果との整合を確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行動更新
  - メモ: 関連Issue: #540
- [x] チェックリスト整合確認
  - メモ: 親タスクと子タスクのチェックを整合
- [x] PR 作成
  - メモ: PR #541 https://github.com/yurake/pptx_generator/pull/541

## メモ
- 連続性メモ（短文で上書き）
  - 前提/制約: paragraph は先頭段落の情報を使用
  - 決定と根拠: 段落間隔と正の first_line_indent を推定に反映
  - リスク(UNCONFIRMED): max_lines 推定の変化でレイアウト選定が変わる可能性
  - Now/Next: Now=レビュー待ち / Next=マージ対応
  - テスト実績/抜け: PYTHONPATH=src python -m pytest tests/utils/test_text_capacity.py / 5 passed / coverage.xml / diff-cover 100%
- 計画のみで完了する場合は、判断者・判断日・次アクション条件を記載する
