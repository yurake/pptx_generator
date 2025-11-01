---
目的: RM-044 ジョブスペック雛形自動生成の仕様設計と実装を完了する
関連ブランチ: feat/rm044-spec-scaffold
関連Issue: #249
roadmap_item: RM-044 ジョブスペック雛形自動生成
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-02 feat/rm044-spec-scaffold を作成。初期コミットは不要（main と同一）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - スコープ: 工程2の `pptx tpl-extract` 実行時にテンプレ由来の `jobspec.json` を生成し、レイアウト名・アンカー・図形タイプなどテンプレ依存情報のみを catalog 化する。章構成や本文は含めず、工程3/4でのマージを前提とする。
    - 対象変更: `src/pptx_generator/models.py` に雛形用モデルを追加し、`src/pptx_generator/pipeline/template_extractor.py` で抽出結果を jobspec に変換、`src/pptx_generator/cli.py` で出力処理を実装。`samples/json/` に `jobspec.json` サンプルを追加し、`README.md`・`docs/requirements/stages/stage-02-template-structure-extraction.md`・`docs/design/design.md` を更新。必要に応じて CLI 統合テストを拡張する。
    - リスク/前提: 既存 `template_spec.json`・`branding.json` の出力互換を維持し、テンプレから取得できない情報は空欄とする。工程5の品質ゲートや監査ログの役割は変えない。ドキュメントで工程3以降とのインターフェースを明記して誤用を防ぐ。
    - テスト: TemplateExtractor ユニットテストで雛形生成を検証し、`uv run pptx tpl-extract samples/templates/templates.pptx` を用いた CLI 統合テストで `jobspec.json` 出力とスキーマ整合、既存成果物への影響がないことを確認する。
    - ロールバック: 追加したモデル・生成処理・ CLI ログ出力・サンプル・ドキュメントを削除し、`pptx tpl-extract` の出力を従来のファイル構成へ戻す。
- [ ] 設計・実装方針の確定
  - メモ: spec_scaffold.json のスキーマ案と CLI/API 連携設計をまとめる。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 必要に応じて docs/requirements および docs/design を更新する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: `tpl-extract` 拡張やスキーマ定義、サンプルデータ生成を実施する。
- [ ] テスト・検証
  - メモ: CLI 経由での生成確認や既存テストの追加・更新を行い結果を記録する。
- [ ] ドキュメント更新
  - メモ: 影響範囲と手順を docs/ 配下に反映し、必要に応じて runbook や README を調整する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 関連 Issue が作成されたら番号を記載する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録し、todo-auto-complete の結果を確認する。

## メモ
- 計画のみで完了する場合は判断者・判断日・次のアクション条件を記載する。
