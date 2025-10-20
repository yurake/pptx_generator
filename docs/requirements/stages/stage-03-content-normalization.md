# 工程3 コンテンツ正規化 (HITL) 要件詳細

## 概要
- 入力データ（Markdown / CSV / JSON 等）をスライド素材へ整形し、ヒューマンレビューで承認を得る。
- RM-005（プレゼンストーリーモデラー）で定義するストーリー構造を参照し、章立て・導入文・キーアングルをカードへ反映する。
- AI が生成した案と人の修正を同時に扱い、承認済み要素はロックする。

## 入力
- ブリーフ情報、案件メモ、既存資料から抽出したテキスト・表。
- 工程2 `layouts.jsonl` から得るレイアウト用途タグ（ヒントとして使用）。
- ブランド・トーン設定、禁則・必須用語。

## 出力
- `content_approved.json`: スライド候補ごとのタイトル、本文、箇条書き、表、意図タグ、ストーリー要素（章分類、ストーリーフェーズ、メッセージアングル）。
- レビューアクションログ: 承認/差戻し/付録送り等の操作履歴。
- AI レビュー結果（グレード、改善提案、Auto-fix 案）。
- `review_engine_analyzer.json`: Analyzer が出力した `issues` / `fixes` を Review Engine が消費できる形式に変換したファイル。スライド単位の `grade`（A/B/C）とサポートされている Auto-fix の JSON Patch を含む。
- ストーリー骨子サマリ: RM-005 で規定する `story_outline.json` などドラフト構成連携用メタデータ。

## ワークフロー
1. AI が候補コンテンツを生成し、カード単位で提示する（章／ストーリーフェーズ案を含む）。
2. レビュワーが API クライアント（CLI や社内ツール）で文面・数値・意図タグを調整する。
3. Auto-fix（安全な軽微修正）を適用し、AI レビューの診断結果とストーリー整合性の警告を確認する。
4. 承認済み要素をロックし、差戻しは理由付きでログ化する。
5. 承認データを `content_approved.json` として確定し、工程4へ送る。

## API 要件
- 認証は OAuth2 Client Credentials（Bearer Token）。未認証時は `401`、権限不足は `403` を返す。
- ETag (`If-Match`) を用いた楽観的ロックを実装し、競合時は `412 Precondition Failed`。
- サポートするエンドポイント（詳細は `docs/design/stages/stage-03-content-normalization.md` 参照）:
  - `POST /v1/content/cards` – 初期カード登録。
  - `PATCH /v1/content/cards/{slide_id}` – 本文・テーブルの更新、Auto-fix 適用。
  - `POST /v1/content/cards/{slide_id}/approve` – 承認・ロック。
  - `POST /v1/content/cards/{slide_id}/return` – 差戻し。
  - `GET /v1/content/cards/{slide_id}` – 最新内容・履歴の取得。
  - `GET /v1/content/logs` – 監査ログ取得（ページング／フィルタ対応）。
- すべての更新系 API は `X-Actor`（操作者）、`X-Request-ID`（トレース ID）ヘッダを必須とする。

## 品質ゲート
- 各カードに必須要素（タイトル・本文）が揃っていること。
- ストーリーフェーズ（導入・課題・解決・効果など）が割り当てられ、章立て整合が保たれていること。
- 数値と単位が整合し、禁則語が含まれていないこと。
- 意図タグが設定されていること。
- Auto-fix 適用箇所がログに記録され、再現可能であること。
- Analyzer の `severity` に応じてスライド単位のグレードが算出され、Review Engine UI で優先度判断に利用できること。

## ログ・インターフェース
- `slide_id`, `action`, `actor`, `timestamp`, `notes` を最小セットとする監査ログ。
- AI レビューの結果（評価レベル A/B/C、改善提案一覧、リスク警告）。
- 差戻し理由と再生成履歴を連携し、再レビュー対象を特定できるようにする。
- Analyzer 連携ログ: `review_engine_analyzer.json` を生成し、`audit_log.json` の `artifacts.review_engine_analysis` へ保存パスを記録する。サポート対象の Auto-fix タイプ（箇条書きレベル調整・フォントサイズ・文字色）のみ JSON Patch として出力し、それ以外は `notes.unsupported_fix_types` に列挙する。

## 未実装項目（機能単位）
- Review Engine UI での新グレード表示と未対応 Fix タイプのハンドリング。
- コンテンツ承認 API と監査ログ整備。
- AI レビューのスコアリングと Auto-fix ワークフロー。
- 禁則語・必須項目のリアルタイム検知ルール。
- ストーリー骨子の生成・編集手順（UI は将来計画、現時点では API を前提）。

## CLI 支援
- `pptx content` コマンドにより、承認済みコンテンツ／レビュー ログを検証したうえで Spec へ適用したスナップショット (`spec_content_applied.json`) とメタ情報 (`content_meta.json`) を生成できる。
- CLI はコメント付き JSON の除去やハッシュ計算を行い、工程5以降で再利用可能な成果物を `.pptx/content/` 配下へ保存する。
- 失敗時は `ContentApprovalError` を返し、未承認カードの有無や JSON バリデーションエラーを検知する。
