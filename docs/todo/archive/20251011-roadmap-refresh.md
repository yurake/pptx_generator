---
目的: 新ロードマップの骨子を策定し、全自動パワポ生成パイプラインの段階的な実装計画をまとめる
関連ブランチ: feat/roadmap-refresh
関連Issue: #165
roadmap_item: RM-015 ロードマップ再設計
---

- [x] まずはブランチ作成とコミット
- [x] 既存ドキュメント（README, AGENTS, roadmap 等）から現行ビジョンと制約を整理する
  - メモ: 自動生成基盤のゴール指標と品質ポリシーを一覧化する
- [x] `docs/notes/20251010-discussion-new-loadmap.txt` を基に全自動パイプラインのステージと入出力を定義する
  - メモ: 1テンプレ準備〜8品質監査までの目的・入力・出力・フォールバックを明文化する
- [x] 新ロードマップ案（6 工程 + 3/4 HITL）のフェーズ構成・成果物・完了条件を整理し、ロードマップ更新方針メモを作成する
  - メモ: フェーズごとの KPI と優先タスクを列挙する
- [x] `docs/roadmap/README.md` を更新し、RM-015 を含む新構成への移行計画を反映する
  - メモ: 既存 RM の継承／廃止判断を記録する
- [x] `AGENTS.md` および関連ガイドの記載対象を整理し、各ドキュメントで参照すべき資料（design/requirements/policies 等）を明示する
  - メモ: `docs/AGENTS.md`, `src/AGENTS.md`, `tests/AGENTS.md` から工程詳細を排除し、参照先や更新手順の指針を加える
- [x] `README.md` と `docs/design/` に新パイプライン（6 工程＋HITL＋AI レビュー）の概要と利用手順を追記する
  - メモ: CLI コマンド例・テンプレ解析 CLI の計画も盛り込む
- [x] `docs/requirements/` と `docs/design/` に承認フロー・AI レビューの状態遷移／スキーマを整理する
  - メモ: プロンプト雛形と Auto-fix の適用条件を明文化する
- [x] `docs/roadmap/README.md` に後続タスク（テンプレ構造抽出 CLI、HITL 実装、AI レビュー）のリンクを追加し、参照 ToDo を紐付ける
- [x] PR 作成
  - メモ: PR #166 https://github.com/yurake/pptx_generator/pull/166（2025-10-11 完了）

## メモ
- 戦略メモは `docs/notes/` に配置し、承認後にロードマップ本体へ反映する
- 文字量とレイアウト制約のフォールバックルールを決定し、品質チェック工程と合わせて整理する
- コンテンツ/HITL 工程（3・4）の承認 UX・権限モデルを別ドキュメントで設計する
