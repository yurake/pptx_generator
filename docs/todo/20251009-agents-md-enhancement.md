---
目的: AGENTS.md を拡充しエージェント向け指示を体系化する
関連ブランチ: feature/agents-md-guidance
関連Issue: 未作成
---

- [x] まずはブランチ作成
  - メモ: 既存の `docs/archive-analyzer-layout` ブランチを継続利用
- [x] 現行ドキュメントの調査 (README, CONTRIBUTING, docs 配下)
  - メモ: README.md, CONTRIBUTING.md, docs/policies/config-and-templates.md からセットアップ・ルールを抽出
- [x] AGENTS.md の章立て案を作成し、必要な追記内容を整理する
  - メモ: セットアップ/CLI/テスト/スタイル/タスク管理/テンプレート注意点の 6 セクションを定義
- [x] AGENTS.md を更新し、抜け漏れチェックを実施する
  - メモ: 新セクションを追加し、主要コマンドと運用フローを記載
- [ ] 参考リポジトリの AGENTS.md 例を収集する
  - メモ: agents.md 公式サイト掲載のサンプルを中心に、主要パターンを洗い出す
- [ ] 収集結果を整理し、AGENTS.md に盛り込むべき項目を洗い出す
  - メモ: 抜け漏れをチェックリスト化して notes に記録する
- [x] コミット粒度に関する運用ルールを追加する
  - メモ: AGENTS.md, docs/policies/task-management.md, docs/todo/README.md に細分化コミットの方針を追記
- [ ] レビュー結果を踏まえて追記を再調整（必要に応じて繰り返し）
  - メモ: フィードバックを反映し、整合性確認後に再度チェックする
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- 参照資料: README.md, CONTRIBUTING.md, docs/policies/config-and-templates.md
- セットアップ・テスト・スタイル・タスク管理・テンプレート運用に関する指示を AGENTS.md に集約済み
- ロードマップ: [docs/roadmap/README.md#エージェント運用ガイド整備（優先度-p1）](../roadmap/README.md#エージェント運用ガイド整備（優先度-p1）) に位置付け
- 反復更新: レビューの度に AGENTS.md と Roadmap の整合性を見直す
- 今後追加された例の参照元や抜粋ポイントもメモに追記すること
- コミット運用ルール追加済み: AGENTS.md, docs/policies/task-management.md, docs/todo/README.md
