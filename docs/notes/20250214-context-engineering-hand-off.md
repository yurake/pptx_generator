# コンテキスト設計ポリシー検討ノート (2025-02-14)

## 背景
- Anthropic の以下の記事を参照し、リポジトリ内ドキュメントの構造と運用指針へ取り入れる方針を検討した。
  - [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  - [Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- 目的は、README / AGENTS / `docs/` 配下の資料を「必要な情報を必要なタイミングで参照できる」形式に揃え、エージェント作業時の前提・参照フローを明確にすること。

## ここまでの整理内容

### 基本ポリシーとして取り込む方針
1. **すべてを upfront コンテキストへ詰め込まない**  
   - README / AGENTS はサマリまでに留め、詳細は Runbook や Design などの参照リンクで提供する。
2. **オンデマンド参照の推奨**  
   - `rg` / `glob` を活用し、必要なファイルを検索して読む手順を明文化する。
3. **ルールとドキュメントを階層構造で管理**  
   - 既存カテゴリ（policies → requirements → design → runbooks → notes）の読み順を守る指針を追加する。
4. **必要な情報を必要な時だけ注入**  
   - Plan / ToDo には参照する資料のリンクのみを記載し、作業中に詳細を都度確認する運用へ寄せる。

### 既存ドキュメントの現状メモ
- `README.md`: 工程・コマンドが詳細に記載されている。冒頭サマリとドキュメント索引を追加する余地あり（まだ未実施）。
- `AGENTS.md`: タスク運用や ToDo 連携を中心に説明。コンテキスト整理ルールの追記が必要。
- `docs/README.md`: カテゴリ一覧は存在。各カテゴリの役割を State/History/Goals 形式で補足する案がある。
- Runbook: 入力・手順・失敗時対応が揃っているものとそうでないものが混在。

### ToDo / Plan 運用への影響
- Plan 承認後に ToDo の「設計・実装方針の確定」で方針メモを記載し、関連ドキュメント（Runbook / Design 等）へのリンクを明示する運用を強化する予定。
- ToDo テンプレートへ「設計・実装方針メモの共有」チェック欄を追加し、参照資料のリンク先を記す案を検討中（まだ未反映）。

## 次に実施するべきタスク案（RM-068 として管理）
1. **policies へのポリシー文書追加**  
   - `docs/policies/context-engineering.md`（仮）を作成し、上記 4 ポイントと README / AGENTS 構成テンプレ、ルール読み順を明文化する。
2. **README / AGENTS の冒頭刷新**  
   - 「目的 → 主要入力 → 主な出力 → 制約 → 参照資料 → チェックリスト」の順に再構成するドラフトを作成。
3. **Runbook のテンプレート化**  
   - 代表的な Runbook を「前提」「入力」「手順」「失敗時」「関連資料」の欄で統一する（既存ファイルの差分調査が必要）。
4. **ToDo テンプレートの更新**  
   - 設計・実装方針メモと参照資料リンクを記載するチェック欄を追加し、Plan → 実装までの流れを強制できるよう調整。
5. **サンプル作業フローのドキュメント化**  
   - 例: 「静的 Blueprint パイプラインを実行する場合」のコンテキストパックを README → Runbook → ToDo の順にどう参照するかをガイドとして残す。

## 補足メモ
- 既存の README / AGENTS を即時に書き換えるのではなく、ガイドライン整備 → 段階的反映の順で進めるのが安全。
- Runbook がスキルの原型になる想定で整理しておくと、将来的に自動化が必要になった際にも対応しやすい。
- 変更反映時は ToDo を作成し、設計・実装方針メモにコンテキストパック要約と参照資料を記載する運用を徹底する。
