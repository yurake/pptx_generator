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
    - 対象整理（スコープ、対象ファイル、前提）: ContentElements および prepare_normalization/content_import/slide_ai/API での本文トリミングを撤廃し、テンプレート由来のレイアウト情報に基づく容量管理へ統一する。Overflow 時は現状警告のみで自動処理は行わず、運用実績を踏まえて再検討する前提。
    - ドキュメント／コード修正方針: モデルのバリデーションから行数・文字数制限を外し、上流 stage の加工ロジックを削除。mapping/generate_ready 等は既存フォールバックと警告出力を維持しつつ挙動を確認。`config/rules.json` から可変閾値を削除し、禁止ワード等のみ残す。変更内容は要件・設計ドキュメントへ反映。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo を stage ごとに更新し、実装後に差分確認結果とテスト結果を共有。必要に応じて docs/notes へ補足を残す。
    - 想定影響ファイル: `src/pptx_generator/models.py`, `pipeline/prepare_normalization.py`, `content_import/service.py`, `slide_ai/client.py`, `pipeline/mapping.py`, `generate_ready.py`, `pipeline/validator.py`, `config/rules.json`, `tests/**`, `docs/requirements/stages/stage-03-compose.md`, `docs/design/schema/stage-03-compose.md` ほか関連資料。
    - リスク: レイアウト許容量を超える長文でレンダリング崩れが発生する恐れ／`rules.json` のキー削除による既存コードの想定外挙動／API・CLI 利用者が長文に未対応のままになる可能性。
    - テスト方針: `uv run --extra dev pytest` を基本とし、時間制約がある場合は models・mapping・CLI 統合テストを優先。必要に応じ `uv run pptx compose`→`pptx gen` で長文維持と警告ログを手動確認。
    - ロールバック方法: `feat/rm068-content-elements` ブランチを削除し、ローカルで `git reset --hard origin/main` → `git checkout main`（ローカル限定）で差分を戻す。
    - 承認メッセージ ID／リンク: チャットメッセージ「ok」（2025-11-24）
- [x] 設計・実装方針の確定
  - メモ: ContentElements/SlideBullet の長さ制限を撤廃し、prepare_normalization・content_import・slide_ai でのトリミング処理を削除。mapping はレイアウトの `max_lines` 超過時に警告のみを出力し、`rules.json` は禁止語など固定ルールのみを保持する方針で確定。
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
- [x] チェックリスト整合確認
  - メモ: 全項目の状態を確認し、親子タスクの整合をチェック済み。
- [x] PR 作成
  - メモ: PR #313 https://github.com/yurake/pptx_generator/pull/313（2025-11-24 完了）

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
- 2025-11-24: Dynamic/Static UAT で判明した差異対応 Plan（承認済み: 本チャットID）
  - スコープ:
    - 動的モードの prepare→draft 変換で bullets / table を構造保持したまま generate_ready.json へ引き継げるよう改修し、既存 ContentElements 互換利用箇所の副作用を抑制する。
    - 静的モードの mapping_log 出力を MappingLog スキーマへ合わせ、Analyzer 連携で ref_id / selected_layout 等を解決できるよう修正する。
  - 影響ファイル（想定）: `src/pptx_generator/pipeline/prepare_normalization.py`, `src/pptx_generator/pipeline/draft_structuring.py`, `src/pptx_generator/models.py`, `tests/**`, `docs/todo/20251124-rm068-content-elements.md`
  - リスク/前提:
    - ContentElements のスキーマ拡張による downstream 影響に注意。LLM 生成ロジックや API レスポンスの互換性確認が必要。
    - 静的 mapping_log フォーマット変更に伴い、既存ログ解析スクリプト（存在する場合）の追随確認。
  - テスト戦略:
    - 単体: prepare_normalization / draft_structuring 周辺の新規ユニットテスト追加。
   - 統合: `uv run --extra dev pytest tests/test_mapping_step.py tests/test_prepare_llm_client.py` を中心に、必要に応じて CLI 統合テストを追加実行。
  - ロールバック: 修正コミットを revert し、`feat/rm068-content-elements` ブランチを承認前状態へ戻す。
- 2025-11-24: 動的テーブルの既存プレースホルダー割り当て Plan（承認済み: 本チャットID）
  - スコープ: 動的モードで生成する `generate_ready.json` のテーブル要素を既存テンプレートプレースホルダーへマッピングし、Stage3/Stage4 の両経路で新規図形生成を抑止する。
  - 影響ファイル（想定）: `src/pptx_generator/pipeline/draft_structuring.py`, `src/pptx_generator/pipeline/mapping.py`, `src/pptx_generator/draft_recommender.py`, `src/pptx_generator/pipeline/table_anchor.py`（新規ヘルパー予定）, `tests/test_draft_structuring_step.py`, `tests/test_mapping_step.py` ほか関連テスト。
  - リスク/前提:
    - レイアウトメタデータに依存したヒューリスティック判定のため、テンプレート命名規則差異で誤マッピングが発生する可能性がある。`table` フォールバックは維持し、警告ログで検知できるようにする。
    - `layouts.jsonl` の `placeholder_summary` 等が欠損する旧フォーマットを考慮し、不足時は安全に現行挙動へフォールバックする。
  - 作業ステップ:
    1. Draft/Mappng 共通で利用できるレイアウト読み込みヘルパーを整備し、プレースホルダー情報を抽出できるようにする。
    2. テーブルアンカーを決定するヒューリスティックを新規ヘルパーへ実装し、Blueprint/明示指定を最優先にしたうえでキーワード・位置情報で候補を絞り込む。
    3. `DraftStructuringStep._merge_slide_elements` を更新し、テーブルをアンカーへ変換したうえで `generate_ready.json` に書き出す。
    4. `MappingStep._build_elements` でも同ヘルパーを適用し、Mapping ログへ割当結果を記録する。
    5. CLI 動的経路の回帰テストを追加し、`generate_ready.json` のテーブルが期待アンカーへ設定されることを検証する。
  - テスト戦略:
    - ユニット: ヒューリスティックの判定ロジックを `tests/test_draft_structuring_step.py` と `tests/test_mapping_step.py` に新規追加して確認。
    - 統合: `uv run --extra dev pytest tests/test_cli_integration.py::test_dynamic_compose_table_anchor`（追加予定）で動的パイプライン全体を検証。必要に応じて既存 CLI シナリオも再実行。
  - ロールバック: 新規ヘルパーと関連変更を revert し、`_merge_slide_elements` / `_build_elements` を現行実装へ戻すことで復旧。
