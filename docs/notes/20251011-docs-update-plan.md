# ドキュメント更新方針まとめ（2025-10-11）

ロードマップ再設計に伴い、既存ドキュメントへ反映すべき事項と編集方針を整理した。  
各ファイルの役割を踏まえ、今回追加された工程（6 フロー構成、3・4 HITL、AI レビュー、共通制約など）をどこに記載すべきかを表にまとめる。

| ドキュメント | 役割（既存運用） | 今回反映する主な内容 | 備考 / 連携先 |
| --- | --- | --- | --- |
| `docs/AGENTS.md` | `docs/` 配下の運用ルール・更新手順を示す | フロー詳細は記さず、「設計・要件の参照先」と「更新時の手順」を追記する（例: 工程変更時は `docs/design/overview.md` と `docs/requirements/overview.md` を更新） | `docs/policies/task-management.md` の Approval ルールと整合させる |
| `src/AGENTS.md` | `src/` の実装ガイド | HITL／AI レビューを実装する際に編集すべきモジュールや参照ドキュメントを追記（例: 新しい JSON は `docs/design/schema-extensions.md` を参照、承認フロー変更時は `tests/AGENTS.md` とペアで更新） | 具体仕様は別資料に記述、指針のみ掲載 |
| `tests/AGENTS.md` | テスト方針と実行ルール | 承認フロー・AI レビュー追加時のテスト対象（スタブ、生成ログ検証、差分比較）と参照先資料 (`docs/design/`, `docs/requirements/`) を追記 | テスト実装時のルールに集中し、仕様本文は引用しない |
| `README.md` | プロジェクト概要と利用手順 | 6 工程と HITL の概要、AI レビューの位置づけを「使い方」章に追記。テンプレ構造抽出 CLI (計画中) の説明と、関連 docs へのリンクを追加 | CLI 使用例 (`uv run pptx-generator …`) とログ出力説明を更新する |
| `docs/design/overview.md` | アーキテクチャとコンポーネント構成 | 工程別責務、承認ステップの状態遷移図、生成される中間 JSON (`content_approved.json`, `draft_approved.json`, `rendering_ready.json`) の I/F を追記 | スキーマ詳細は `schema/` に分離し、相互リンク |
| `docs/design/schema/README.md` | JSON スキーマや I/F 拡張 | 新しい承認中間データのスキーマ、レイアウトスコアリング指標、AI レビュー結果スキーマ（Auto-fix など）を追記 | 実装時はここを参照して `models.py` を調整 |
| `docs/requirements/overview.md` | ビジネス／機能要件 | HITL 承認基準（3/4）、AI レビュー評価レベル (A/B/C) と適用条件、監査項目 (source_id/template_version/content_hash) を追加 | KPI とロードマップの整合を確認し、必要に応じて `docs/roadmap/` とリンク |
| `docs/policies/config-and-templates.md` | テンプレ／設定の運用ポリシー | 画像・チャート制約（ロゴのみ、テキスト構造化のみ）やテンプレ版管理の追加ルールを明文化 | テンプレ更新手順の追記。`docs/notes/20251011-roadmap-refresh.md` 参照案内 |
| `docs/policies/task-management.md` | Approval-First Policy | HITL で新設される承認ゲート（工程 3/4）を追記し、Plan/承認フローとの整合を取る | ToDo 運用の接続（部分承認時のログ化など）も確認 |
| `docs/requirements/overview.md` | 品質・機能要件 | 追加 KPI（承認 5 分以内、AI レビュー適用率など）の記載。テンプレ解析 CLI の性能目標 | 監査ログ要件と同時に更新 |
| `docs/roadmap/README.md` | テーマ単位の進行管理 | フェーズ A/B/C に対応する後続タスク（テンプレ解析 CLI、HITL 実装、AI レビュー実装）のリンクを追加し、参照 ToDo を明記 | RM-015 セクションから関連 ToDo を逆リンク |
| `docs/notes/20251011-roadmap-refresh.md` | 戦略メモ | 設計・要件ドキュメントとのリンク（上記の参照先）を記載し、ノートから本資料へ誘導 | 追記後に `docs/notes/20251011-discussion-digest.md` と相互リンク |

この方針に従い、各ファイルの更新時には ToDo へ進捗を記載し、関連するロードマップ／ノートからリンクを張る。
