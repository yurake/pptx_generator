---
目的: Renderer でブランド段落スタイルを適用し Polisher 依存を縮小する
関連ブランチ: feat/rm034-paragraph-style
関連Issue: #220
roadmap_item: RM-034 Renderer 段落スタイル再設計
---

- [x] ブランチ作成と初期コミット
  - メモ: ブランチ名や初期コミット内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
  - メモ: 2025-10-20 ブランチ `feat/rm034-paragraph-style` 作成済み。初期コミット `docs(todo): add RM-034 renderer paragraph style task` を登録済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認取得済メッセージや後続判断予定を記入する
  - メモ: 2025-10-20 ユーザー承認済（本スレッド Plan への OK 応答）。
- [x] 設計・実装方針の確定
  - メモ: レビューや追加調整が必要な場合は記載する
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点はユーザーへ相談した結果を残す
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: branding 段落インデント拡張と Renderer 適用処理を実装。未対応: Polisher 側の整理は今後対応。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_renderer.py tests/test_settings.py` を実行し、23 件成功。
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 2025-10-20 `docs/policies/config-and-templates.md` と `docs/notes/20251019-polisher-scope-review.md` を更新。roadmap 反映は別途検討。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: `関連Issue: #220` を反映済み。追加ログは ToDo と PR で追跡する。
- [x] PR 作成
  - メモ: PR #223 https://github.com/yurake/pptx_generator/pull/223（2025-10-20 完了）

## メモ
- 設計時にブランド設定と python-pptx のインデント単位差の整理が必要。
- 2025-10-20 サポート runbook と README を更新し、Polisher がフォールバック補正に限定される運用と Renderer による段落スタイル適用を明記。
