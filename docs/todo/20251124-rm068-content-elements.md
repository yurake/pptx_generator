---
目的: RM-068 ContentElements 制約見直し
関連ブランチ: feat/rm068-content-elements
関連Issue: #305
roadmap_item: RM-068 ContentElements 制約見直し
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm068-content-elements ブランチを main から作成。初期コミットは `docs(todo): add rm068 content-elements todo` で ToDo 追加。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: ContentElements および prepare_normalization/content_import/content_ai/API での本文トリミングを撤廃し、テンプレート由来のレイアウト情報に基づく容量管理へ統一する。Overflow 時は現状警告のみで自動処理は行わず、運用実績を踏まえて再検討する前提。
    - ドキュメント／コード修正方針: モデルのバリデーションから行数・文字数制限を外し、上流工程の加工ロジックを削除。mapping/generate_ready 等は既存フォールバックと警告出力を維持しつつ挙動を確認。`config/rules.json` から可変閾値を削除し、禁止ワード等のみ残す。変更内容は要件・設計ドキュメントへ反映。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo を工程ごとに更新し、実装後に差分確認結果とテスト結果を共有。必要に応じて docs/notes へ補足を残す。
    - 想定影響ファイル: `src/pptx_generator/models.py`, `pipeline/prepare_normalization.py`, `content_import/service.py`, `content_ai/client.py`, `pipeline/mapping.py`, `generate_ready.py`, `pipeline/validator.py`, `config/rules.json`, `tests/**`, `docs/requirements/stages/stage-03-mapping.md`, `docs/design/schema/stage-03-mapping.md` ほか関連資料。
    - リスク: レイアウト許容量を超える長文でレンダリング崩れが発生する恐れ／`rules.json` のキー削除による既存コードの想定外挙動／API・CLI 利用者が長文に未対応のままになる可能性。
    - テスト方針: `uv run --extra dev pytest` を基本とし、時間制約がある場合は models・mapping・CLI 統合テストを優先。必要に応じ `uv run pptx compose`→`pptx gen` で長文維持と警告ログを手動確認。
    - ロールバック方法: `feat/rm068-content-elements` ブランチを削除し、ローカルで `git reset --hard origin/main` → `git checkout main`（ローカル限定）で差分を戻す。
    - 承認メッセージ ID／リンク: チャットメッセージ「ok」（2025-11-24）
- [x] 設計・実装方針の確定
  - メモ: ContentElements/SlideBullet の長さ制限を撤廃し、prepare_normalization・content_import・content_ai でのトリミング処理を削除。mapping はレイアウトの `max_lines` 超過時に警告のみを出力し、`rules.json` は禁止語など固定ルールのみを保持する方針で確定。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 上記方針を本 ToDo へ反映済み。追加資料は今回不要。
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件／設計ドキュメントへ新方針を反映済み（Stage2/Stage3 の仕様更新と rules.json の役割変更を明記）。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: モデル・パイプライン・CLI ・設定ファイルを更新し、長文保持と overflow 警告のみの挙動へ統一。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_models.py tests/test_settings.py tests/test_mapping_step.py` を実行し、14 件成功。
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [x] docs/roadmap 配下（RM-068 項目の成果内容を更新）
  - [x] docs/requirements 配下（Stage3 要件を新方針へ更新）
  - [x] docs/design 配下（Schema/ステージ設計の記述を更新）
  - [x] docs/runbook 配下（今回変更不要である旨確認）
  - [x] README.md / AGENTS.md（今回変更不要である旨確認）
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
