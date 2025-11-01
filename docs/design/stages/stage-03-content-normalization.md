# 工程3 コンテンツ正規化 (HITL) 設計

## 目的
- 入力データをスライド素材に整形し、人の承認と AI レビューを統合する。
- 承認済みコンテンツを `content_approved.json` として後工程に渡す。
- 現時点では専用 UI は提供せず、API／CLI を通じて HITL 承認を運用する（UI は将来拡張としてバックログ管理）。

## システム構成
| レイヤ | コンポーネント | 概要 |
| --- | --- | --- |
| クライアント層 | （将来拡張） | 現時点では専用 UI は提供せず、CLI や社内ツールから API を利用 |
| サービス層 | Content Service API | コンテンツ CRUD、承認管理、ログ出力 |
| AI 補助 | Review Engine | LLM & ルールベースの診断と Auto-fix 提案 |
| ストレージ | Content Store | `content_draft.json`, `content_approved.json`, Review Logs |

## データモデル
- `content_card`: `slide_uid`, `title`, `body`, `table_data`, `intent_tag`, `status`
- `review_log`: `slide_uid`, `action`, `actor`, `timestamp`, `notes`, `ai_grade`, `auto_fix_applied`
- `auto_fix_patch`: JSON Patch 互換形式で差分を表現

## ワークフロー
1. Input Processor が `spec.json` を分解しカードを生成。  
2. Review Engine が初期診断（A/B/C）と提案を付与。  
3. レビュワーが API クライアント（CLI や社内ツール）で修正、Auto-fix 適用、差戻しを行う。  
4. `Approve` で `content_approved.json` へ反映しロック。  
5. 差戻しは `status=rework` として再生成対象に戻す。

### 多形式インポート基盤
- 目的: JSON 以外のプレーンテキスト、PDF、URL から内容を安全に取り込み、カード生成前に共通中間フォーマットへ統合する。
- 入力判定: CLI で `--content-source <path|url>` を指定し、拡張子／スキームでアダプタを選択。複数指定時は順番通りにマージし、重複スライド ID は後勝ちのルールで解決する。
- アーキテクチャ
  - `TextImportAdapter`: UTF-8 文字列または `.txt` を読み込み、章見出し記法と空行をキーにカード化する。
  - `PdfImportAdapter`: `soffice --headless --convert-to txt` でテンポラリに変換し、テキストと画像埋め込みのプレースホルダメタを抽出する。LibreOffice 失敗時はフォールバックせずにエラー終了。
  - `UrlImportAdapter`: `requests` ベースで HTML/JSON を取得し、Content-Type に応じて本文ブロックを抽出。HTML は本文テキストのみをプレーン化し、リンク URL をメタ情報として保持。
  - すべてのアダプタは `NormalizedItem`（`id`, `title`, `body`, `attachments`, `source_meta`）を返し、Input Processor が Slide に変換する。
- 監査とリトライ
  - 正常時は `audit_log.json` に `content_import` セクションを追加し、ファイルハッシュ／URL／取得時刻／使用許諾フラグを記録。
  - 失敗時はリトライポリシー（デフォルト 3 回、指数バックオフ）を適用し、限界超過で `content_import_error` イベントを発行して処理全体を中断する。
  - PDF 変換や URL 取得で検知した警告は `content_review_log` に `source_warning` として残し、HITL が再入力を判断できるようにする。
  - LibreOffice (soffice) が利用できない環境では PDF 取込テストが実施できないため、導入後に再検証する運用ルールを `docs/todo/` に明記する。

### 生成AIオーケストレーション
- 目的: 生成AIポリシーを外部設定で切り替えながら、Spec を入力にスライド草案を自動生成する。
- 設計要素
  - ポリシー設定: `config/content_ai_policies.json` に複数ポリシーを定義し、`default_policy_id` を起点に CLI から選択する。`prompt_id` と `intent` を紐付け、実際のテンプレート文字列は `src/pptx_generator/content_ai/prompts.py` で管理する。
  - オーケストレーター: `ContentAIOrchestrator` が Spec・ポリシー・LLM クライアント（当面はモック）を組み合わせて `ContentApprovalDocument` を構築し、生成ログ／メタ情報を返す。
  - LLM クライアント: `MockLLMClient` は Spec のスライド情報を利用して本文候補を組み立て、長さ制限（40 文字×6 行）を満たすよう調整する。将来は実サービスのクライアントと差し替える。
- CLI 挙動: `pptx content` 実行時は生成AIモードをデフォルトとし、`--content-source` や `--content-approved` を指定した場合のみ外部入力／承認ファイルモードへ切り替える。`--ai-policy`（定義ファイル上書き）、`--ai-policy-id`（ポリシー ID）、`--ai-output`（生成ログ）、`--ai-meta`（メタ情報）を任意で指定できる。
- ログ: 生成AIモードで `-v/--verbose` または `--debug` を指定すると、プロンプトとレスポンスの概要がログ出力される。
- LLM プロバイダーは環境変数 `PPTX_LLM_PROVIDER` で選択する。サポート対象は `mock` / `openai` / `azure-openai` / `claude` / `aws-claude`。各プロバイダー固有の API キーやエンドポイントは README の表に従って設定する。
- 出力成果物
  - `content_draft.json`: 生成された `ContentApprovalDocument`。`status=draft` のスライド群として後工程のレビュー対象になる。
  - `ai_generation_meta.json`: ポリシー ID、モデル名、Spec ハッシュ、スライドごとの `content_hash`・意図タグ・行数。
  - `content_ai_log.json`: スライド単位のプロンプト、警告、利用モデルなど監査目的のログ。
- トーンと禁則を `safeguards` にまとめ、`ContentDocumentMeta.tone` へ反映させる。禁則語やポリシー更新手順は今後 `docs/policies/config-and-templates.md` に追記する。

### Analyzer 連携
- CLI の工程 6 実行後、Analyzer が出力する `analysis.json` を Review Engine 向け形式 (`review_engine_analyzer.json`) に変換するアダプタを追加した。  
- スライドごとの `issues` を `AIReviewIssue` へマッピングし、`severity` に応じて `grade`（`A/B/C`）を算出する。  
- `bullet_reindent` / `bullet_cap` / `font_raise` / `color_adjust` は JSON Patch 形式の Auto-fix (`AutoFixProposal`) として出力し、未対応タイプは `notes.unsupported_fix_types` に記録する。  
- 出力ファイルは `analysis.json` と同じディレクトリに `review_engine_analyzer.json` として保存し、`audit_log.json` の `artifacts.review_engine_analysis` にもパスを記録する。

## API 概要
- `POST /content/cards`: 初期カード作成
- `PATCH /content/cards/{slide_uid}`: 編集・Auto-fix 適用
- `POST /content/cards/{slide_uid}/approve`: 承認
- `POST /content/cards/{slide_uid}/return`: 差戻し
- `GET /content/logs`: 审査ログ出力

## API 詳細設計

### 共通仕様
- Base URL: `/v1`
- 認証: `Authorization: Bearer <token>`（OAuth2 Client Credentials を想定）。認証エラー時は `401`、権限不足は `403`。
- リクエスト/レスポンス形式: `application/json; charset=utf-8`
- 競合制御: 変更系 API は `If-Match` ヘッダで ETag（`content_cards/{slide_uid}` のバージョン）を受け取り、`412 Precondition Failed` で競合を通知。
- 監査メタ: すべての変更系 API は `X-Actor`（ユーザー ID）、`X-Request-ID`（呼び出しトレース）ヘッダを必須とする。
- エラー形式:
  ```json
  {
    "error": "validation_error",
    "message": "意図タグが未指定です",
    "details": [
      {"field": "intent", "issue": "missing"}
    ]
  }
  ```

### エンドポイント

#### `POST /v1/content/cards`
- 用途: `content_draft.json` 相当の初期カードを登録し、レビュープロセスを開始する。
- リクエスト
  ```json
  {
    "spec_id": "job-20251017-001",
    "cards": [
      {
        "slide_id": "agenda",
        "title": "アジェンダ",
        "body": [
          "背景整理",
          "提案サマリー"
        ],
        "table_data": null,
        "intent": "outline",
        "story": {
          "phase": "introduction",
          "chapter_id": "ch-01",
          "angle": "背景整理"
        }
      }
    ]
  }
  ```
- レスポンス `201 Created`
  ```json
  {
    "spec_id": "job-20251017-001",
    "revision": "W/\"cards-5\""
  }
  ```

#### `PATCH /v1/content/cards/{slide_id}`
- 用途: カード本文・テーブル・メタ情報の更新と Auto-fix 適用。
- リクエスト
  ```json
  {
    "title": "アジェンダ（更新）",
    "body": [
      "背景整理（承認済み）",
      "提案サマリー（承認済み）"
    ],
        "table_data": {
          "headers": ["マイルストーン", "時期"],
          "rows": [["キックオフ", "2025 Q1"]]
        },
    "intent": "outline",
    "story": {
      "phase": "introduction",
      "chapter_id": "ch-01",
      "angle": "背景整理"
    },
    "autofix_applied": ["p-agenda-bullet"]
  }
  ```
- レスポンス `200 OK`
  ```json
  {
    "revision": "W/\"cards-6\"",
    "content_hash": "sha256:1b12..."
  }
  ```
- 主なエラー: `400 validation_error`（必須項目不足）、`404 not_found`、`409 conflict`（承認済みカードへの更新）、`412 precondition_failed`（ETag 不一致）。

#### `POST /v1/content/cards/{slide_id}/approve`
- 用途: カードの承認・ロック。Auto-fix 済みのパッチ ID を同時に記録。
- リクエスト
  ```json
  {
    "notes": "承認済み。AI 提案 p01 反映済み。",
    "applied_autofix": ["p01"]
  }
  ```
- レスポンス `200 OK`
  ```json
  {
    "revision": "W/\"cards-7\"",
    "status": "approved",
    "locked_at": "2025-10-17T10:05:00+09:00"
  }
  ```

#### `POST /v1/content/cards/{slide_id}/return`
- 用途: 差戻し。理由と再生成トリガーを記録。
- リクエスト
  ```json
  {
    "reason": "禁則語を含むため修正が必要",
    "requested_by": "reviewer@example.com"
  }
  ```
- レスポンス `200 OK`
  ```json
  {
    "status": "returned",
    "revision": "W/\"cards-8\""
  }
  ```

#### `GET /v1/content/cards/{slide_id}`
- 用途: 最新のカード内容とレビュー履歴を取得。
- レスポンス `200 OK`
  ```json
  {
    "slide_id": "agenda",
    "title": "アジェンダ（承認済み）",
    "body": [
      "背景整理（承認済み）",
      "提案サマリー（承認済み）"
    ],
        "table_data": null,
    "intent": "outline",
    "story": {
      "phase": "introduction",
      "chapter_id": "ch-01",
      "angle": "背景整理"
    },
    "status": "approved",
    "revision": "W/\"cards-7\"",
    "history": [
      {
        "action": "approve",
        "actor": "editor@example.com",
        "timestamp": "2025-10-17T10:05:00+09:00",
        "notes": "承認済み。AI 提案 p01 反映済み。",
        "applied_autofix": ["p01"]
      }
    ]
  }
  ```

#### `GET /v1/content/logs`
- 用途: 承認ログ、差戻し履歴を一覧取得（監査・モニタリング用）。
- クエリ: `?spec_id=job-20251017-001&action=approve&since=2025-10-01T00:00:00Z&limit=100`
- レスポンス `200 OK`
  ```json
  {
    "items": [
      {
        "spec_id": "job-20251017-001",
        "slide_id": "agenda",
        "action": "approve",
        "actor": "editor@example.com",
        "timestamp": "2025-10-17T10:05:00+09:00",
        "notes": "承認済み。AI 提案 p01 反映済み。",
        "applied_autofix": ["p01"],
        "ai_grade": "A"
      }
    ],
    "next_offset": null
  }
  ```

### バリデーション・監査ルール
- `title` / `intent` / `story.phase` は必須。ASCII 制御文字は禁止。
- `body` は 6 行以内、各行 40 文字以内。超過時は `400 validation_error` を返す。
- `table_data.rows` は `headers` と同じ列数である必要がある。違反時は `400`.
- `autofix_applied` は JSON Patch ID と一致するフォーマット (`[a-z0-9-]+`) に制限。
- 承認処理は同じ `slide_id` に対して多重に呼び出された場合でも冪等となるよう、既に承認済みなら `200` で現在の状態を返す。
## AI レビュー連携
- ルール検証（禁則、数値、文字数）→ `critical` なら自動差戻し。
- LLM 評価はメッセージ構造化 (`grade`, `strengths`, `weaknesses`, `actions`) に揃える。
- Auto-fix は JSON Patch と自然文（説明）をセットで保存。

## エラーハンドリング
- 承認済みカードへの編集要求 → `409 Conflict`
- LLM エラー → 既存レビュー結果を保持しリトライフラグ付与
- 保存失敗 → Draft スナップショットからロールバック

## モニタリング
- メトリクス: 承認完了時間、Auto-fix 適用率、差戻し率、LLM 失敗率。
- ログ: API アクセスログ、AI 呼び出しログを統合して監査（将来的に専用 UI を追加する場合は操作ログを拡張）。

## テスト戦略
- API 単体・統合テスト（FastAPI 予定）。UI E2E は対象外。
- AI レビュー: 固定入力で determinism を確認、メトリクスのみ比較。

## 未解決事項
- オフライン承認（CLIベース）サポートの UX 整備。
- 欠損テーブル編集時のオペレーション（API クライアント側での UX）。
- Review Engine のスケール戦略（同期 vs 非同期処理）。

## 関連スキーマ
- [docs/design/schema/stage-03-content-normalization.md](../schema/stage-03-content-normalization.md)
- サンプル: [docs/design/schema/samples/content_approved.jsonc](../schema/samples/content_approved.jsonc)
