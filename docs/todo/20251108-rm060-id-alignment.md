---
目的: Stage3 Drafter が JobSpec と BriefCard の ID を自動整合させ、不一致カードを検知前に補正する
関連ブランチ: fix/rm060-stage3-id-enforce
関連Issue: 未作成
roadmap_item: RM-060 Stage3 ID 整合性強制
---

- [x] ブランチ作成と初期コミット
  - メモ: fix/rm060-stage3-id-enforce ブランチを継続利用。前タスクで ID 検出の実装とテストを完了済み。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ:
    - 目的: `prepare_card.json.cards[*].card_id` と JobSpec `slides[*].id` のマッピングを DraftStructuring 前段で自動調整し、ID が存在しないカードを最優先の採用候補から補正する。
    - 前提: JobSpec 側に複数候補（例: layout/phase/タイトル）がある場合、カード属性から最適なスライド ID を選定して一致させる必要がある。
- [ ] 設計・実装方針の確定
- [ ] ドキュメント更新（要件・設計）
  - メモ: 新しい整合ロジックと優先順位、フォールバック条件を整理する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
- [ ] テスト・検証
  - メモ: CLI / pipeline レベルのテストで補正後に DraftStructuring が成功するケースを追加。
- [ ] ドキュメント更新
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
- [ ] PR 作成

## メモ
-
