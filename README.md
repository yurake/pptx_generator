<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/pptx_generator_logo_black.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/pptx_generator_logo_white.png">
    <img src="assets/pptx_generator_logo_white.png" alt="PPTX GENERATOR">
  </picture>
</p>


PowerPoint テンプレートと資料データ（プレーンテキストや PDF など）を取り込み、テンプレートに沿ったプレゼン資料を生成する CLI ツールです。

## 主な機能
- PPTX テンプレートからレイアウト構造とブランド設定を抽出し、再利用可能な プレゼン仕様 JSON を自動生成する。
- 資料データ（プレーンテキストや PDF など）とプレゼン仕様 JSON を取り込み、PPTX を生成し、必要に応じて LibreOffice 経由で PDF を併産する。

## アーキテクチャ概要
本プロジェクトは 4 工程で資料を生成します。詳細は `docs/design/design.md` を参照してください。

| 工程 | 入力 | 出力 | 主な出力先 | 概要 |
| --- | --- | --- | --- | --- |
| 1. テンプレ | テンプレートPPTX(`templates.pptx`) | テンプレ仕様(`jobspec.json`) | `.pptx/extract/` | テンプレ整備・抽出・検証・リリースメタ生成をワンフローで実施し、後続工程の基盤データを用意 |
| 2. コンテンツ準備 | 資料データ(text,PDFなど)、<br>テンプレ仕様(`jobspec.json`)  | ドラフト(`prepare_card.json`) | `.pptx/prepare/` | 入力データをスライド候補へ整形し、生成AIを併用しながら正規化を行う |
| 3. マッピング | テンプレ仕様(`jobspec.json`)、<br>ドラフト(`prepare_card.json`) | パワポ生成input(`generate_ready.json`) | `.pptx/draft/`, `.pptx/compose/` | 章構成承認とレイアウト割付をまとめて実施し、ドラフトとマッピング成果物を生成 |
| 4. PPTX生成 | パワポ生成input(`generate_ready.json`)  | `proposal.pptx`、`proposal.pdf` | `.pptx/gen/` | テンプレ適用と最終出力を生成し、整合チェックと監査メタを記録（デフォルト出力先は `.pptx/gen/`） |

```mermaid
flowchart TD
  %% ======= Styles =======
  classDef stage fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,font-weight:bold;
  classDef file fill:#f3f4f6,stroke:#4b5563,stroke-width:1px,color:#111827,font-weight:bold;
  classDef userfile fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#064e3b,font-weight:bold;
  classDef final fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#78350f,font-weight:bold;

  %% ======= Stage 1 =======
  Tmpl["**テンプレートPPTX (templates.pptx)**"]:::userfile --> S1["**工程 1 テンプレ**"]:::stage
  S1 --> Jobspec["**テンプレ仕様(jobspec.json)**"]:::file

  %% ======= Stage 2 =======
  Brief["**資料データ (brief_source.md / .json)**"]:::userfile --> S2["**工程 2 コンテンツ準備**"]:::stage
  S2 --> BriefCards["**ドラフト(prepare_card.json)**"]:::file
  BriefCards --> S3

  %% ======= Stage 3 =======
  S3["**工程 3 マッピング**"]:::stage
  Jobspec --> S3
  S3 --> Ready["**パワポ.json (generate_ready.json)**"]:::file

  %% ======= Stage 4 =======
  Ready --> S4["**工程 4 PPTX生成**"]:::stage
  S4 --> PPTX["**proposal.pptx**"]:::final
  S4 --> PDF["**proposal.pdf**"]:::final

  %% ======= Legend =======
  subgraph Legend[凡例]
    direction LR
    A1["**工程（自動/HITL）**"]:::stage
    A2["**システム生成ファイル**"]:::file
    A3["**ユーザー準備ファイル**"]:::userfile
    A4["**最終成果物**"]:::final
  end
```



### セットアップ
1. Python 3.12 系の仮想環境を用意し、有効化します。
2. 依存パッケージを同期します。
   ```bash
   uv sync
   ```
3. CLI が動作することを確認します。
   ```bash
   uv run --help
   ```
4. (任意)パワポのPDF出力を実施したい場合は、LibreOffice を導入し headless 実行を確認します。
   ```bash
   soffice --headless --version
   ```
5. (任意、基本不要)パワポの仕上げツールを利用する場合は .NET 8 SDK をインストールします。

## CLI チートシート

| 工程 | コマンド例 | 主な出力 | 補足 |
| --- | --- | --- | --- |
| 1. テンプレ | `uv run pptx template samples/templates/templates.pptx` | `.pptx/extract/template_spec.json`, `.pptx/extract/jobspec.json`, `.pptx/extract/branding.json` | テンプレ抽出と検証を一括実行。`--with-release --brand demo --version v1` を付与するとテンプレのメタ情報を生成。 |
| 2. コンテンツ準備 | `uv run pptx prepare samples/contents/sample_import_content_summary.txt` | `.pptx/prepare/prepare_card.json` | プレーンテキスト等の非構造化データを取り込み正規化 |
| 3. マッピング| `uv run pptx compose .pptx/extract/jobspec.json --brief-cards .pptx/prepare/prepare_card.json --template samples/templates/templates.pptx` | `.pptx/draft/generate_ready.json` | 章構成承認とレイアウト割付をまとめて実行 |
| 4. PPTX生成 | `uv run pptx gen .pptx/compose/generate_ready.json --branding .pptx/extract/branding.json --export-pdf` | `.pptx/gen/proposal.pptx`, `proposal.pdf` | `generate_ready.json` に記録されたテンプレ情報を用いて最終成果物を生成（`--output` 未指定時は `.pptx/gen/` へ出力）。 |

補足:
- 要件は `docs/requirements/requirements.md`、アーキテクチャは `docs/design/design.md`、CLI 詳細は `docs/design/cli-command-reference.md`、運用メモは `docs/runbooks/` を参照してください。
- 1.テンプレの個別サブコマンド（`tpl-extract` / `layout-validate` / `tpl-release`）や中間成果物の詳細は `docs/design/cli-command-reference.md` を参照してください。
- 3.マッピンングの個別サブコマンド（ `outline` / `mapping` ）の詳細は `docs/runbooks/story-outline-ops.md` を参照してください。


## 工程別ガイド概要
ここでは各工程の目的と主要な参照ドキュメントをまとめます。詳細な手順やチェックリストはリンク先を参照してください。

### 原則
- CLI の詳細なオプションは各サブコマンドに対して `uv run pptx <cmd> --help` を参照してください。
- `pptx` ルートコマンドには `-v/--verbose`（INFO レベル）と `--debug`（DEBUG レベル）のログオプションがあります。生成AIモードのプロンプト／レスポンス詳細はこれらのオプションを付与した場合に出力されます。

### 工程 1: テンプレ工程
- テンプレ資産は `templates/` で管理し、命名規約や更新手順は `docs/policies/config-and-templates.md` を参照します。
- 抽出と検証は `uv run pptx template` で一括実行します。リリースメタが必要な場合は `--with-release --brand <brand> --version <ver>` を付与してください。
  ```bash
  uv run pptx template templates/libraries/<brand>/<version>/template.pptx \
    --output .pptx/extract/<brand>_<version> \
    --with-release --brand <brand> --version <version>
  ```
  - 既定の出力先は `.pptx/extract/` です。抽出成果物に加え、`--with-release` 指定時は `.pptx/release/` に `template_release.json` や `release_report.json` が生成されます。
- 個別コマンド（`tpl-extract` / `layout-validate` / `tpl-release`）やゴールデンサンプル運用は `docs/design/cli-command-reference.md` の「テンプレ工程詳細オプション」を参照してください。
- 要件と品質ゲートは `docs/requirements/stages/stage-01-template-pipeline.md` に集約しています。

### 工程 2: コンテンツ準備
- ブリーフ入力（Markdown / JSON）を `BriefCard` モデルへ整形し、AI ログや監査メタ付きの成果物一式を `.pptx/prepare/` 配下に生成します。生成カード枚数は `--card-limit` で制御可能です。
- ガイドラインは `docs/requirements/stages/stage-02-content-normalization.md` を参照してください。
- 代表的な実行例:
- `.pptx/prepare/` 配下に `prepare_card.json`、`brief_log.json`、`brief_ai_log.json`などを出力します。
  ```bash
  uv run pptx prepare samples/contents/sample_import_content_summary.txt \
    --output .pptx/prepare
  ```
  - 主な生成物: `prepare_card.json`, `brief_log.json`, `brief_ai_log.json`, `ai_generation_meta.json`, `brief_story_outline.json`, `audit_log.json`
  - 既存の承認済み Brief を再利用する場合は `--brief-cards`, `--brief-log`, `--brief-meta` を Stage3 に直接渡します（Stage2 をスキップ可能）。

### 工程 3: マッピング (HITL + 自動)
- 章構成承認とレイアウト割付を同一工程で扱い、`generate_ready.json`・`generate_ready_meta.json`・`draft_review_log.json`・`draft_mapping_log.json` を同時に更新します。
- 推奨コマンドは `pptx compose` で、HITL 差戻しや再実行時も一貫した出力ディレクトリ（既定 `.pptx/draft/`）を維持します。
  ```bash
  uv run pptx compose .pptx/extract/jobspec.json \
    --brief-cards .pptx/prepare/prepare_card.json \
    --brief-log .pptx/prepare/brief_log.json \
    --brief-meta .pptx/prepare/ai_generation_meta.json \
    --draft-output .pptx/draft \
    --layouts .pptx/extract/layouts.jsonl
  # 完了後に `.pptx/draft/generate_ready.json` や `draft_mapping_log.json` を確認
  ```
- `pptx gen` は工程4のレンダリングコマンドであり、ここで生成した `generate_ready.json` を入力として利用します。

### 工程 4: PPTX レンダリング
- `pptx gen` サブコマンドで `generate_ready.json` を入力し、PPTX／PDF（任意）と監査ログを生成します。
  ```bash
  uv run pptx gen .pptx/compose/generate_ready.json \
    --output .pptx/gen \
    --branding config/branding.json \
    --export-pdf
  ```
- `generate_ready.json` に `meta.template_path` が記録されていれば、`--template` を指定せずにテンプレートを自動解決します。
- 詳細ガイド: `docs/requirements/stages/stage-04-rendering.md` と `docs/design/stages/stage-04-rendering.md`

## 主な成果物
- 最終成果物（`proposal.pptx` や任意の `proposal.pdf`）および中間ファイルの一覧は `docs/design/design.md` を参照してください。

## 詳細コマンドリファレンス
- 4 工程パイプラインと各コマンドの責務・主要オプションは `docs/design/cli-command-reference.md` を参照してください。

## テスト・検証
- 全体テスト: `uv run --extra dev pytest`
- CLI 統合テストのみ: `uv run --extra dev pytest tests/test_cli_integration.py`
- テスト実行後は `.pptx/compose/` や `.pptx/gen/`、`.pptx/extract/` の成果物を確認し、期待する PPTX／PDF／ログが生成されているかをチェックします。テスト方針の詳細は `tests/AGENTS.md` を参照してください。

## 設定リファレンス
| ファイル | 役割 | 変更時に参照するドキュメント |
| --- | --- | --- |
| `config/rules.json` | 文字数上限・段落レベル・禁止ワードなど検証ルールを定義 | `docs/policies/config-and-templates.md` |
| `config/branding.json` | フォント・配色・レイアウト個別設定を管理する `layout-style-v1` スキーマ | `config/AGENTS.md` |

テンプレ抽出やリリースの詳細な運用フローは `docs/design/cli-command-reference.md` および `docs/design/design.md` のテンプレ関連節を参照してください。

## 開発ガイドライン
- コントリビューション規約は `CONTRIBUTING.md` にまとめています。
- `docs/AGENTS.md`（ドキュメント更新ルール）や `src/AGENTS.md`（実装ガイド）を併読してください。
- 主な静的解析コマンド:
  ```bash
  uv tool run --package ruff ruff check .
  uv tool run --package black black --check .
  uv tool run --package mypy mypy src
  ```
- .NET 関連の整形は `dotnet format` を利用します。

## 参考ドキュメント
- `docs/design/design.md`: アーキテクチャ全体像
- `docs/design/schema/README.md`: 中間 JSON スキーマと AI レビュー仕様
- `docs/requirements/requirements.md`: ビジネス／機能要件
- `docs/requirements/stages/stage-0x-*.md`: 各工程の詳細要件
- `docs/notes/20251012-readme-refactor.md`: README リファクタリングの検討メモ
- `docs/roadmap/roadmap.md`: ロードマップとテーマ一覧

## ライセンス / サポート
- ライセンス: 社内利用を前提としており、公開ライセンスは未定です。
- 運用・問い合わせフローは `docs/runbooks/support.md` を参照してください。
