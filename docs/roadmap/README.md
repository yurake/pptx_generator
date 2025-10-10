# 開発ロードマップ（大項目）

## 運用方針
- ブランチや PR を跨ぐ開発テーマを本ページで俯瞰し、ステータスの起点とする。
- 各テーマに紐づくタスク詳細は `docs/todo/` 配下で管理し、必ず相互リンクを張る。
- 進捗は「完了済み小項目数 / 総小項目数」を原則とし、更新日は ISO 形式で明記する。
- 評価指標や背景の議事は `docs/notes/` と `docs/requirements/`、設計変更は `docs/design/` を参照する。

## 全体目標と指標
- **北極星指標**: 月次で社内提案書 120 件を自動生成し、手戻り率（再提出件数 / 総件数）10% 以下を達成する。
- **品質指標**: Analyzer が検知する `critical` issue を 1 ジョブあたり平均 0.5 件以下に抑える。
- **効率指標**: 30 スライド構成を 60 秒以内で PPTX + PDF 出力まで完了させる。
- **運用指標**: 監査ログの欠損率 0% を維持し、ジョブ失敗時の再実行時間を 5 分以内とする。

## フェーズ別マイルストーン
| フェーズ | 期間 | 目的 | 主要アウトプット |
| --- | --- | --- | --- |
| フェーズ1: 出力一貫化 | 2025-10-05 〜 2025-10-31 | PPTX 生成から PDF 配布までの自動フロー確立 | LibreOffice 連携 CLI、PDF 保存仕様、テストスイート拡張 |
| フェーズ2: 品質診断強化 | 2025-11-01 〜 2025-11-30 | Analyzer/Refiner の重大度判定と自動補正の拡充 | `analysis.json` スキーマ拡張、Fix ルール追加、UI 向けサマリーレポート |
| フェーズ3: 運用安定化 | 2025-12-01 〜 2026-01-15 | 監査・通知・設定管理の自動化 | 監査ログ基盤、ジョブリトライ運用、通知チャネル整備 |

## アクティブテーマ
- テーマごとに `RM-xxx` 番号を付与し、ToDo フロントマターの `roadmap_item` と一致させる。

<a id="rm-001"></a>
### RM-001 Analyzer / Refiner ルール拡張（優先度: P2）
- ゴール: 品質診断と自動補正の精度を高め、要件定義書 4.3〜4.4 節の達成度を引き上げる。
- 参照ドキュメント: [docs/requirements/overview.md](../requirements/overview.md), [docs/design/overview.md](../design/overview.md)
- 参照 ToDo: [docs/todo/archive/20251007-analyzer-layout-consistency.md](../todo/archive/20251007-analyzer-layout-consistency.md)
- 状況: 実装中（2025-10-07 更新）
- 期待成果: `contrast_low` 判定の調整、`layout_consistency` 追加、Fix ログの監査連携。
- 次のアクション: `contrast_low` 判定の調整方針整理、Analyzer レポートのモニタリング指標の整理、Fix ログ可視化要件の精査。

<a id="rm-003"></a>
### RM-003 ビジュアルフィードバックコパイロット（優先度: P3）
- ゴール: 生成されたスライドに対し、視覚モデル＋LLM がリアルタイムで「目線導線」「情報の密度」「ブランド逸脱」を可視化し、プレゼンターが WOW と感じる改善提案を提示する。
- 参照ドキュメント: [docs/design/overview.md](../design/overview.md)
- 状況: 調査中（2025-10-05 更新）
- 期待成果: スライド PNG + 幾何情報を入力としたフィードバック API、ダッシュボード UI モック、Fix への反映ルール策定。
- 依存: 画像生成モデルの選定、GPU 実行基盤、Analyzer ログとの連携。
- 次のアクション: 参考事例のリサーチ、モデル推論コスト試算、UI プロトタイピング。

<a id="rm-004"></a>
### RM-004 営業ナレッジ連携自動化（優先度: P4）
- ゴール: CRM や案件管理システムから取得した勝ちパターン・競合情報を提案書自動生成に組み込み、ユーザーにとっての「次の一手」を提案する。
- 参照ドキュメント: [docs/requirements/overview.md](../requirements/overview.md)
- 状況: 準備中（2025-10-05 更新）
- 期待成果: CRM 連携スキーマ定義、勝因レビューの LLM 要約、提案書内へのサジェストブロック挿入。
- 依存: CRM API トークン管理、個人情報マスキング、ジョブスケジューラ。
- 次のアクション: 主要フィールドの洗い出し、プライバシー要件の確認、最初の連携 PoC 設計。

<a id="rm-005"></a>
### RM-005 プレゼンストーリーモデラー（優先度: P5）
- ゴール: ユーザーの案件メモやディスカッションログから、提案書のストーリーラインを AI が共同設計し、アウトラインとスライド骨子を自動生成する。
- 参照ドキュメント: [docs/notes/20251004-initial-deiscussion.txt](../notes/20251004-initial-deiscussion.txt), [docs/requirements/overview.md](../requirements/overview.md)
- 状況: 企画中（2025-10-05 更新）
- 期待成果: `Service-A Outliner` の高度化、感情トーンや意思決定ステージに合わせたストーリーパターン生成、アウトライン差分レビュー UI。
- 依存: LLM プロンプト設計、ユーザー入力メタデータ（客先業界・想定読者）の整備。
- 次のアクション: ユースケース別ストーリーテンプレートの整理、プロトタイプ用プロンプトの作成。

<a id="rm-006"></a>
### RM-006 ライブ共同編集アシスト（優先度: P6）
- ゴール: 提案会議中でも AI がライブでスライド修正案・説明コメント・補足資料リンクを提示し、即応性の高いプレゼンを実現する。
- 参照ドキュメント: [docs/design/overview.md](../design/overview.md)
- 状況: アイデア段階（2025-10-05 更新）
- 期待成果: WebSocket ベースの共同編集プロトコル設計、リアルタイム要約と修正提案、セッション監査ログ。
- 依存: 低遅延インフラ、アクセス制御、UI コンポーネント設計。
- 次のアクション: 技術スタック比較、遅延要件の整理、UI ワイヤーフレーム作成。

<a id="rm-007"></a>
### RM-007 SlideBullet アンカー拡張（優先度: P2）
- ゴール: SlideBullet 要素がテンプレート内の任意テキスト図形へ挿入できるようレンダラーを拡張し、複数レイアウトでの再利用性を高める。
- 参照ドキュメント: [docs/AGENTS.md](../AGENTS.md)
- 参照 ToDo: [docs/todo/20251010-renderer-slidebullet-anchor.md](../todo/20251010-renderer-slidebullet-anchor.md)
- 状況: 検討中（2025-10-10 更新）
- 期待成果: JSON 仕様でのアンカー指定対応、BODY 固定以外のテキスト形状選択、CLI テストとサンプルでの検証。
- 依存: テンプレートレイアウト命名規則、Open XML SDK による仕上げ処理、PDF 変換時の段落整形。
- 次のアクション: 既存レンダラー実装のアンカー前提調査、仕様追加案の整理、サンプルとテストの更新計画策定。

<a id="rm-015"></a>
### RM-015 テンプレート命名整合性チェッカー（優先度: P3）
- ゴール: テンプレート内で同一スライドに重複するプレースホルダー／図形名を検出し、アンカー指定時の衝突を防ぐ運用・実装フローを整える。
- 参照ドキュメント: [docs/policies/config-and-templates.md](../policies/config-and-templates.md)
- 参照 ToDo: （未作成 — 着手時に `docs/todo/` へ登録）
- 状況: 未着手（2025-10-11 追加）
- 期待成果: テンプレート読込時の名称衝突検知、CLI への警告出力、プレースホルダー命名規則の追加ガイド。
- 依存: RM-008（カスタムテンプレート操作性向上）のアンカー実装、テンプレート運用ポリシー、CLI 構成の拡張余地。
- 次のアクション: 要件整理と PoC 設計、検知ロジック導入先の選定、専用 ToDo の作成。

<a id="rm-009"></a>
### RM-009 テンプレート設定自動生成（優先度: P2）
- ゴール: PPTX テンプレートから `config/branding.json` 同等のスタイル定義を自動生成し、ブランド設定保守の手間を削減する。
- 参照ドキュメント: 未整備（本テーマで作成予定）
- 参照 ToDo: [docs/todo/20251009-branding-config-generator.md](../todo/20251009-branding-config-generator.md)
- 状況: 調査中（2025-10-09 更新）
- 期待成果: 抽出対象となるフォント・配色情報の整理、python-pptx で取得可能な属性の調査結果、変換フロー（CLI / スクリプト）の方向性。
- 依存: python-pptx のスタイル取得制約、LibreOffice / Open XML SDK での補完可否、ブランド設定 JSON のスキーマ拡張余地。
- 次のアクション: テンプレート XML 解析とスタイル情報マッピングの調査、補完ルール案の作成、試作ワークフローのステップ定義。

<a id="rm-010"></a>
### RM-010 テンプレート仕様エクスポート（優先度: P2）
- ゴール: PPTX テンプレートから `samples/json/sample_spec.json` 作成に必要なレイアウト・アンカー情報を自動抽出し、JSON 作成工数を削減する。
- 参照ドキュメント: 未整備（本テーマで作成予定）
- 参照 ToDo: [docs/todo/20251009-template-spec-export.md](../todo/20251009-template-spec-export.md)
- 状況: 企画中（2025-10-09 更新）
- 期待成果: レイアウト一覧と図形名のエクスポート手順の確立、サンプル JSON 雛形生成のプロトタイプ、テンプレート命名規則ガイドの更新案。
- 依存: python-pptx の図形情報取得機能、テンプレート側でのアンカー命名整備、サンプルデータ更新ポリシー。
- 次のアクション: 抽出対象属性の整理、エクスポートスクリプトの PoC 方針検討、関連ドキュメントの改訂計画作成。

<a id="rm-011"></a>
### RM-011 レイアウトスタイル統一（優先度: P3）
- ゴール: テーブル・チャート・画像などのレイアウトスタイルを設定ファイルで統一管理し、ブランド統一感を維持できるようにする。
- 参照ドキュメント: 未整備（RM-010 完了後に ToDo を作成予定）
- 状況: 構想中（2025-10-09 更新）
- 期待成果: レイアウト用設定スキーマ整備、レンダラーでのスタイル適用、サンプルとテストの更新。
- 依存: RM-008（アンカー混在対応）、RM-010（テンプレート仕様エクスポート）、`config/branding.json` の拡張設計。
- 次のアクション: RM-010 の成果を踏まえた設計レビュー、設定項目の洗い出し、着手時に新規 ToDo を作成。
- 備考: レイアウト仕様をエクスポートし資料化する拡張は RM-010 完了後に新規 Roadmap として検討する。

<a id="rm-012"></a>
### RM-012 レンダラーテキスト強化（優先度: P1）
- ゴール: スライドのサブタイトル・ノート・テキストボックスを含む文章要素をレンダラーで描画し、基本レイアウト要件を満たす。
- 参照ドキュメント: [docs/design/overview.md](../design/overview.md), [docs/notes/20251009-feature-gap-analysis.md](../notes/20251009-feature-gap-analysis.md)
- 状況: 未着手（2025-10-09 設定）
- 期待成果: `Slide.subtitle` と `notes` の描画処理実装、`slides[].textboxes[]` スキーマと描画サポート、サンプル／テストの反映。
- 依存: RM-007（SlideBullet アンカー拡張）の仕様調整、`samples/templates/` のレイアウト更新、CLI 統合テスト。
- 次のアクション: スキーマ拡張の設計レビュー、レンダラー実装方針の決定、対応 ToDo の発行。

<a id="rm-013"></a>
### RM-013 PPTX 解析アナライザー実装（優先度: P1）
- ゴール: 生成された PPTX を解析して幾何・スタイル情報を収集し、`grid_misaligned` など設計済みルールを含む品質診断を実現する。
- 参照ドキュメント: [docs/requirements/overview.md](../requirements/overview.md), [docs/design/overview.md](../design/overview.md), [docs/notes/20251009-feature-gap-analysis.md](../notes/20251009-feature-gap-analysis.md)
- 状況: 未着手（2025-10-09 設定）
- 期待成果: PPTX 読み取りロジックと issue/fix 出力、既存 JSON ベース診断からの移行計画、テストデータ（PPTX）を用いた検証。
- 依存: LibreOffice / Open XML SDK 等の解析ツール選定、RM-012 で追加する描画仕様、CI 環境でのバイナリ比較手法。
- 次のアクション: 解析対象項目の優先順位付け、PoC スクリプト作成、適用ルールとメトリクスの整理。

<a id="rm-014"></a>
### RM-014 自動補正・仕上げ統合（優先度: P1）
- ゴール: Refiner の自動補正範囲を拡張し、Open XML SDK ベースの Polisher を組み込んで仕上げ工程を自動化する。
- 参照ドキュメント: [docs/design/overview.md](../design/overview.md), [docs/notes/20251009-feature-gap-analysis.md](../notes/20251009-feature-gap-analysis.md)
- 状況: 未着手（2025-10-09 設定）
- 期待成果: フォントサイズ引き上げ・色調整などの安全な自動適用、Polisher プロジェクト雛形と CLI 連携、監査ログへの補正記録。
- 依存: RM-013 の解析結果、.NET 8 実行環境、テンプレート運用ポリシーの更新。
- 次のアクション: 自動補正ポリシーの定義、Open XML SDK ベース実装のスコープ見直し、対応 ToDo とテスト計画の策定。

## バックログ（優先検討）
- `Service-F Distributor` の通知チャネル整備（Teams / Slack）と監査ログ統合。運用要件（docs/requirements/overview.md の 5. 出力と配布）で求められる保存先連携・通知を実現し、`docs/notes/20251009-feature-gap-analysis.md` の指摘に基づき優先度を再評価する。
- CLI / REST API の認証方式統一（OAuth2 / SAS トークン）とキー管理ドキュメントの追加。
- `reverse_engineer.py` PoC による既存 PPTX からの spec 逆生成検討。

## 完了テーマ

<a id="rm-002"></a>
### RM-002 エージェント運用ガイド整備（優先度: P1）
- ゴール: エージェントが参照する AGENTS.md と連動ドキュメントを体系化し、開発プロセスやテンプレート準備手順を一元管理する。
- 参照ドキュメント: [AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../CONTRIBUTING.md), [docs/policies/config-and-templates.md](../policies/config-and-templates.md)
- 参照 ToDo: [docs/todo/20251009-samples-expansion.md](../todo/20251009-samples-expansion.md)
- 状況: 完了（2025-10-10 更新）
- 期待成果: テンプレート準備ガイドの整備に加え、最小構成・フル構成サンプルの提供と活用ドキュメントの拡充。

### PDF 自動生成対応
- ゴール: PPTX 生成直後に PDF 化までを自動化し、配布用資料をワンステップで提供する。
- 参照 ToDo: [docs/todo/archive/20251005-pdf-export-automation.md](../todo/archive/20251005-pdf-export-automation.md)
- 状況: 10 件中 10 件完了（2025-10-06 更新）
- 成果: PR #143 https://github.com/yurake/pptx_generator/pull/143

### パイプライン機能拡張
- ゴール: JSON スキーマ拡張と自動診断強化によって生成品質を底上げする。
- 参照 ToDo: [docs/todo/archive/20251004-pipeline-enhancements.md](../todo/archive/20251004-pipeline-enhancements.md), [docs/todo/archive/20251010-auto-complete-archive-handling.md](../todo/archive/20251010-auto-complete-archive-handling.md)
- 状況: 7 件中 7 件完了（2025-10-06 更新）、追加修正 1 件完了（2025-10-10 更新）
- 成果: スキーマ拡張、Analyzer 出力整備、テスト追加、関連ドキュメント更新。
- 追加成果: auto_complete_todo.py でアーカイブ済み ToDo の成功判定を実装（PR #146）。

### レンダラー リッチコンテンツ対応
- ゴール: 表・画像・グラフをブランドスタイル付きで描画できるレンダラーを実装する。
- 参照 ToDo: [docs/todo/archive/20251005-renderer-rich-content.md](../todo/archive/20251005-renderer-rich-content.md)
- 状況: 14 件中 14 件完了（2025-10-06 更新）
- 成果: リッチコンテンツ描画処理、テンプレート改善、検証手順の追加。

<a id="rm-008"></a>
### RM-008 カスタムテンプレート操作性向上（優先度: P2）
- ゴール: プレースホルダー名称を活用して画像・テーブル・チャートを配置し、テンプレート側で図形種類を固定しなくてもアンカー指定が有効になる状態を実現する。
- 参照 ToDo: [docs/todo/archive/20251009-placeholder-anchor.md](../todo/archive/20251009-placeholder-anchor.md)
- 状況: 完了（2025-10-10 更新）
- 期待成果: プレースホルダーと図形のアンカー混在対応、テンプレート準備ガイドの更新、回帰テストによる互換性確認。
- 依存: レンダラーのアンカー解決ロジック、テンプレート操作ドキュメント、CLI テストスイート。

## 更新履歴
- 2025-10-05: 初版作成。
- 2025-10-05: 全体目標、フェーズ計画、バックログを追記。
- 2025-10-06: PDF 自動生成の実装状況と監査ログ出力機能を追記。
- 2025-10-07: PDF 自動生成対応を完了テーマへ移動。
- 2025-10-09: RM-002 を再開し、サンプル拡充タスクと参照ドキュメントを追記。
- 2025-10-09: RM-012〜RM-014 を追加し、通知チャネル整備のバックログ情報を更新。
