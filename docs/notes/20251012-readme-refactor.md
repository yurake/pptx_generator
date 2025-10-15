# README リファクタリング検討メモ（2025-10-12）

`README.md` の現状と改善案を整理する。主な論点は「一般的に記載すべき章構成の棚卸し」と「アーキテクチャ概要（6 工程）と使い方の整合」である。

## 現状整理

| セクション | 現在の内容 | 課題・不足 | 対応方針 |
| --- | --- | --- | --- |
| プロジェクト概要 | 冒頭にツールの目的と特徴を簡潔に記載 | 主要機能（HITL 必須工程、テンプレ構造抽出、PDF 変換など）の整理が不足 | 冒頭で提供価値とコア機能を箇条書きで明示 |
| アーキテクチャ概要 | 6 工程を説明し、参照ドキュメントを案内 | 工程と CLI コマンドの対応が README 内では不明瞭 | 後続の「使い方」で工程と具体操作を対応付け |
| セットアップ | Python 仮想環境と `uv sync` のみ記載 | .NET 8 / LibreOffice / `uv run --help` 検証など CONTRIBUTING との乖離 | 必須ツールと確認コマンドを列挙、権限対策 (`UV_CACHE_DIR`) を追記 |
| 使い方 | `pptx gen` と `tpl-extract` を中心にコマンド列挙 | 6 工程のうち HITL や計画中機能との関係が不明。分析結果の出力場所が断片的 | 工程ごとに「現在の進め方」「対応コマンド」「HITL/計画中」を整理。`analysis.json` など出力整理 |
| オプション表 | `pptx gen` / `tpl-extract` の主要オプションを整理済み | CLI サブコマンド追加に備えた導線 (spec 生成など) が不明 | 将来計画はメモ程度に留め、詳細は `docs/notes/` やロードマップに誘導 |
| テスト・検証 | pytest 実行方法のみ記載 | `uv run --extra dev pytest tests/test_cli_integration.py` など部分的案内が不足 | CONTRIBUTING の内容と揃え、CLI 統合テストや出力確認手順を追加 |
| 設定 | `config` の 2 ファイルのみ | ブランド設定やテンプレ運用ポリシーへの導線不足 | `config/AGENTS.md` や `docs/policies/config-and-templates.md` へのリンクを追加 |
| 開発者向け情報 | セクション自体が欠けている | CONTRIBUTING, AGENTS への導線や lint/format 方針が README から辿れない | 「開発ガイドライン」節を追加し、主要資料へのリンク集を提供 |
| コントリビューション | 未記載 | 外部/社内問わず貢献プロセスの案内が無い | CONTRIBUTING.md へ誘導する節を追加 |
| ライセンス / サポート | 未記載 | OSS としての扱い・窓口が不明 | ライセンスの有無を明示し、問い合わせ先／内部運用ポリシーを記載 |

## 使い方章の再構成案

1. **全体フローの把握**: `docs/design/overview.md` を参照し、工程 1〜6 の位置づけを理解する。
2. **工程別の操作ガイド**
   - 工程 1: テンプレ準備（手動／既存資産管理）— 現状はテンプレ管理ポリシーを参照する。CLI 対応は計画中である旨を明記。
   - 工程 2: `uv run pptx tpl-extract` でテンプレ構造抽出。出力物（レイアウト JSON、`branding.json`）と保存先を説明。
   - 工程 3: コンテンツ正規化（HITL）。`docs/requirements/stages/stage-03-...` など参照し、ワークシート例を記載。自動化は今後の検討と記載。
   - 工程 4: ドラフト構成設計（HITL）。`draft_approved.json` の作成例と進行状況を説明。
   - 工程 5: `rendering_ready.json` を生成するマッピング工程（自動）。現状は CLI 実装中で、手順は設計ドキュメントを案内。
   - 工程 6: `uv run pptx gen` 実行で PPTX/PDF を生成。出力ディレクトリとログを整理し、`--export-pdf` オプションや LibreOffice 依存を明記。
3. **成果物の確認**: `.pptx/gen/` や `outputs/audit_log.json`、PDF 出力の確認方法をまとめる。

## その他の加筆ポイント

- 依存ツールのバージョン要件（Python 3.12 系、.NET 8、LibreOffice）を「セットアップ」と「環境要件」に明示する。
- `uv run --help` による CLI エントリーポイント確認、`UV_CACHE_DIR=.uv-cache` を使った権限対策を記載する。
- テスト節に CLI 統合テストコマンドと出力確認プロセスを追加し、`tests/AGENTS.md` へのリンクを張る。
- 「参考ドキュメント」「関連ポリシー」節で `docs/AGENTS.md` / `docs/policies/task-management.md` / `docs/policies/config-and-templates.md` を案内する。
- ライセンスが未整備である旨と、社内限定利用を想定している場合はその旨を明記する。（公開方針が確定していないため、暫定表記でも良い）

このメモを踏まえて README を再構成する。
