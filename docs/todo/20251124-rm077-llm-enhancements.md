---
目的: RM-077 LLM ラベル整備
関連ブランチ: feat/rm077-llm-enhancements
関連Issue: 未作成
roadmap_item: RM-077 LLM ラベル整備
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm077-llm-enhancements を作成し、`docs: add todo for rm077 llm enhancements` を作成済み。push は未実施。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `.github/issue-labeler.yml` / `.github/labeler.yml` に `area:llm` を追加し、`docs/policies/github-label-governance.md` で運用ルールを更新する。LLM 関連ディレクトリとキーワード定義を整理し、既存ラベルとの整合を保つ。
    - ドキュメント／コード修正方針: ラベルポリシーに表とルールを追記し、Issue/PR 自動付与設定へパターンを追加。設定変更は YAML フォーマットを崩さないよう手動編集し、必要に応じて `yq` / `jq` で検証する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 変更内容はこの ToDo と `docs/roadmap/roadmap.md` の RM-077 セクションに記録し、PR 説明にも `area:llm` 追加の背景を記載する。
    - 想定影響ファイル: `.github/issue-labeler.yml`, `.github/labeler.yml`, `docs/policies/github-label-governance.md`, `docs/roadmap/roadmap.md`（状況更新のみ）。
    - リスク: 正規表現やグロブ誤設定による誤ラベル付与。既存ワークフローが失敗する可能性。導入直後は対象 PR/Issue で結果を確認し、誤りがあれば即時修正する。
    - テスト方針: `yamllint` 相当のチェックは手元にないため、`python -m compileall` 同等の構文検査は行わず `yq` で読み込み確認する。必要に応じて `act` で `labeler` ワークフローのドライランを実施する。
    - ロールバック方法: 追加した `area:llm` 行を削除して元の YAML を復元し、ポリシードキュメントの該当セクションを revert する。
    - 承認メッセージ ID／リンク: ユーザー承認「ok」（2025-11-24 の会話メッセージ）を参照。
- [ ] 設計・実装方針の確定
  - メモ: 
- [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
- [ ] ドキュメント更新（要件・設計）
  - メモ: 確定した設計・実装方針を要件／設計ドキュメントへ反映し、変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 
- [ ] テスト・検証
  - メモ: 
- [ ] ドキュメント更新
  - メモ: 
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
