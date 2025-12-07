# 図作成 CLI 使用例

このドキュメントでは、スケジュール作成、組織図作成、開発要員計画作成のCLI使用方法を説明します。

## 概要

| コマンド | 説明 | テンプレート |
|---------|------|--------------|
| `schedule` | スケジュールガントチャート作成 | `templates.pptx` |
| `organization` | 組織図作成 | `organization_templates.pptx` |
| `development-personnel` | 開発要員計画作成 | `development_personnel_templates.pptx` |

## ディレクトリ構成

```
src/pptx_generator_schedule/
├── samples/
│   ├── schedule/                     # スケジュール作成用
│   │   ├── schedule.md               # 入力Markdown
│   │   └── output/                   # 出力ディレクトリ
│   ├── organization/                 # 組織図作成用
│   │   ├── organization.md           # 入力Markdown
│   │   └── output/                   # 出力ディレクトリ
│   ├── development_personnel/        # 開発要員計画作成用
│   │   ├── schedule.md               # 入力Markdown（スケジュール情報）
│   │   ├── personnel_data.xlsx       # 入力Excel（工数データ）
│   │   └── output/                   # 出力ディレクトリ
│   └── templates/                    # テンプレートPPTX
│       ├── templates.pptx            # スケジュール用
│       ├── organization_templates.pptx  # 組織図用
│       └── development_personnel_templates.pptx  # 開発要員計画用
└── CLI_USAGE.md                      # このドキュメント
```

---

## 1. スケジュール作成

Markdownファイルからスケジュールガントチャート（矢羽型）を生成します。

### 基本コマンド

```bash
uv run pptx schedule src/pptx_generator_schedule/samples/schedule/schedule.md \
  --template src/pptx_generator_schedule/samples/templates/templates.pptx
```

### オプション

| オプション | 説明 | デフォルト値 |
|-----------|------|-------------|
| `--template`, `-t` | テンプレートPPTXファイル | 必須 |
| `--output`, `-o` | 出力ディレクトリ | `src/pptx_generator_schedule/samples/schedule/output` |
| `--year` | 対象年 | 現在年 |
| `--branding` | ブランド設定ファイル | `config/branding.json` |
| `--layout` | 使用するレイアウト名 | `白紙` |

### カスタム出力ディレクトリを指定

```bash
uv run pptx schedule src/pptx_generator_schedule/samples/schedule/schedule.md \
  --template src/pptx_generator_schedule/samples/templates/templates.pptx \
  --output /path/to/custom/output
```

### 出力ファイル

| ファイル | 説明 |
|---------|------|
| `schedule_data.json` | 中間生成ファイル（パース結果） |
| `schedule_gantt.pptx` | 生成されたPPTXファイル |

---

## 2. 組織図作成

Markdownファイルから組織図を生成します。

### 基本コマンド

```bash
uv run pptx organization src/pptx_generator_schedule/samples/organization/organization.md \
  --template src/pptx_generator_schedule/samples/templates/organization_templates.pptx
```

### オプション

| オプション | 説明 | デフォルト値 |
|-----------|------|-------------|
| `--template`, `-t` | テンプレートPPTXファイル | 必須 |
| `--output`, `-o` | 出力ディレクトリ | `src/pptx_generator_schedule/samples/organization/output` |
| `--title` | 組織図のタイトル | `組織図` |
| `--branding` | ブランド設定ファイル | `config/branding.json` |
| `--layout` | 使用するレイアウト名 | `System_layout` |

### カスタム出力ディレクトリを指定

```bash
uv run pptx organization src/pptx_generator_schedule/samples/organization/organization.md \
  --template src/pptx_generator_schedule/samples/templates/organization_templates.pptx \
  --output /path/to/custom/output
```

### 出力ファイル

| ファイル | 説明 |
|---------|------|
| `organization_data.json` | 中間生成ファイル（パース結果） |
| `organization_chart.pptx` | 生成されたPPTXファイル |

---

## 3. 開発要員計画作成

Markdownファイル（スケジュール情報）とExcelファイル（工数データ）から開発要員計画スライドを生成します。

### 基本コマンド

```bash
uv run pptx development-personnel \
  src/pptx_generator_schedule/samples/development_personnel/schedule.md \
  --xlsx src/pptx_generator_schedule/samples/development_personnel/personnel_data.xlsx \
  --template src/pptx_generator_schedule/samples/templates/development_personnel_templates.pptx
```

### オプション

| オプション | 説明 | デフォルト値 |
|-----------|------|-------------|
| `--xlsx` | 工数データのxlsxファイル | 必須 |
| `--template`, `-t` | テンプレートPPTXファイル | 必須 |
| `--output`, `-o` | 出力ディレクトリ | `src/pptx_generator_schedule/samples/development_personnel/output` |
| `--branding` | ブランド設定ファイル | `config/branding.json` |
| `--layout` | 使用するレイアウト名 | `System_layout` |
| `--use-ai` | AIを使用してxlsxを解析 | `false` |
| `--ai-backend` | AIバックエンド（`anthropic` / `bedrock`） | `anthropic` |
| `--ai-model` | AIモデル | デフォルトモデル |
| `--ai-region` | Bedrockのリージョン | `us-east-1` |

### カスタム出力ディレクトリを指定

```bash
uv run pptx development-personnel \
  src/pptx_generator_schedule/samples/development_personnel/schedule.md \
  --xlsx src/pptx_generator_schedule/samples/development_personnel/personnel_data.xlsx \
  --template src/pptx_generator_schedule/samples/templates/development_personnel_templates.pptx \
  --output /path/to/custom/output
```

### AI解析モード

様々なExcelフォーマットに対応するため、AIを使用してxlsxを解析できます。

#### Anthropic Claude API を使用

```bash
export ANTHROPIC_API_KEY="your-api-key"

uv run pptx development-personnel \
  src/pptx_generator_schedule/samples/development_personnel/schedule.md \
  --xlsx src/pptx_generator_schedule/samples/development_personnel/personnel_data.xlsx \
  --template src/pptx_generator_schedule/samples/templates/development_personnel_templates.pptx \
  --use-ai \
  --ai-backend anthropic
```

#### Amazon Bedrock (Claude) を使用

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

uv run pptx development-personnel \
  src/pptx_generator_schedule/samples/development_personnel/schedule.md \
  --xlsx src/pptx_generator_schedule/samples/development_personnel/personnel_data.xlsx \
  --template src/pptx_generator_schedule/samples/templates/development_personnel_templates.pptx \
  --use-ai \
  --ai-backend bedrock \
  --ai-region us-east-1
```

### 出力ファイル

| ファイル | 説明 |
|---------|------|
| `personnel_data.json` | 中間生成ファイル1（xlsxパース結果） |
| `development_personnel_plan.json` | 中間生成ファイル2（統合結果） |
| `development_personnel.pptx` | 生成されたPPTXファイル |

---

## 入力ファイルフォーマット

### schedule.md（スケジュール）

```markdown
## フェーズ1：企画・設計
# プロジェクト計画・要件定義
開始: 2024年度4月
終了: 2024年度7月
# 基本設計
開始: 2024年度6月
終了: 2024年度9月

## フェーズ2：開発
# 詳細設計
開始: 2024年度8月
終了: 2024年度11月
# 製造・単体テスト
開始: 2024年度10月
終了: 2025年度2月

---
# マイルストーン
要件定義完了: 2024年度7月
基本設計完了: 2024年度9月
```

### organization.md（組織図）

```markdown
## カテゴリー名
# グループ名
メンバー1
メンバー2
```

### personnel_data.xlsx（工数データ）

フェーズごとの担当者別月別工数を記載したExcelファイル。
`--use-ai` オプションを使用すると、様々なフォーマットに対応できます。

---

## ヘルプの表示

```bash
# 全コマンドの一覧
uv run pptx --help

# 各コマンドのヘルプ
uv run pptx schedule --help
uv run pptx organization --help
uv run pptx development-personnel --help