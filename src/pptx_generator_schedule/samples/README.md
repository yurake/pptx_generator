# pptx_generator_schedule サンプルファイル

このディレクトリには、図作成CLIのサンプルファイルが含まれています。

## ディレクトリ構造

```
samples/
├── schedule/                     # スケジュール作成用
│   ├── schedule.md               # スケジュール入力Markdown
│   └── output/                   # サンプル出力
│       └── schedule_data.json    # 中間生成ファイル
├── organization/                 # 組織図作成用
│   ├── organization.md           # 組織図入力Markdown
│   └── output/                   # サンプル出力
│       └── organization_data.json # 中間生成ファイル
├── development_personnel/        # 開発要員計画作成用
│   ├── schedule.md               # スケジュール入力Markdown
│   ├── personnel_data.xlsx       # 工数データExcel
│   └── output/                   # サンプル出力
│       ├── personnel_data.json   # 中間生成ファイル1
│       └── development_personnel_plan.json  # 中間生成ファイル2
└── templates/                    # テンプレートPPTX
    ├── templates.pptx                        # スケジュール用テンプレート
    ├── organization_templates.pptx           # 組織図用テンプレート
    └── development_personnel_templates.pptx  # 開発要員計画用テンプレート
```

## 使用方法

各CLIコマンドのデフォルト出力ディレクトリは `src/pptx_generator_schedule/samples/` 配下に設定されています。

### 1. スケジュール作成

スケジュール用テンプレート: `templates.pptx`

```bash
# デフォルト出力: src/pptx_generator_schedule/samples/schedule/output/
uv run pptx schedule src/pptx_generator_schedule/samples/schedule/schedule.md \
  --template src/pptx_generator_schedule/samples/templates/templates.pptx
```

カスタム出力ディレクトリを指定する場合:
```bash
uv run pptx schedule src/pptx_generator_schedule/samples/schedule/schedule.md \
  --template src/pptx_generator_schedule/samples/templates/templates.pptx \
  --output /path/to/custom/output
```

### 2. 組織図作成

組織図用テンプレート: `organization_templates.pptx`

```bash
# デフォルト出力: src/pptx_generator_schedule/samples/organization/output/
uv run pptx organization src/pptx_generator_schedule/samples/organization/organization.md \
  --template src/pptx_generator_schedule/samples/templates/organization_templates.pptx
```

カスタム出力ディレクトリを指定する場合:
```bash
uv run pptx organization src/pptx_generator_schedule/samples/organization/organization.md \
  --template src/pptx_generator_schedule/samples/templates/organization_templates.pptx \
  --output /path/to/custom/output
```

### 3. 開発要員計画作成

開発要員計画用テンプレート: `development_personnel_templates.pptx`

```bash
# デフォルト出力: src/pptx_generator_schedule/samples/development_personnel/output/
uv run pptx development-personnel \
  src/pptx_generator_schedule/samples/development_personnel/schedule.md \
  --xlsx src/pptx_generator_schedule/samples/development_personnel/personnel_data.xlsx \
  --template src/pptx_generator_schedule/samples/templates/development_personnel_templates.pptx
```

カスタム出力ディレクトリを指定する場合:
```bash
uv run pptx development-personnel \
  src/pptx_generator_schedule/samples/development_personnel/schedule.md \
  --xlsx src/pptx_generator_schedule/samples/development_personnel/personnel_data.xlsx \
  --template src/pptx_generator_schedule/samples/templates/development_personnel_templates.pptx \
  --output /path/to/custom/output
```

#### AI解析モード（様々なExcelフォーマットに対応）

**Anthropic Claude API:**
```bash
export ANTHROPIC_API_KEY="your-api-key"
uv run pptx development-personnel \
  src/pptx_generator_schedule/samples/development_personnel/schedule.md \
  --xlsx src/pptx_generator_schedule/samples/development_personnel/personnel_data.xlsx \
  --template src/pptx_generator_schedule/samples/templates/development_personnel_templates.pptx \
  --use-ai \
  --ai-backend anthropic
```

**Amazon Bedrock (Claude):**
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
AI解析モードを使用すると、様々なフォーマットに対応できます。

## 出力ファイル

各コマンドは以下のファイルを生成します：

| コマンド | 中間ファイル | 出力PPTX |
|---------|------------|----------|
| schedule | `schedule_data.json` | `schedule_gantt.pptx` |
| organization | `organization_data.json` | `organization_chart.pptx` |
| development-personnel | `personnel_data.json`, `development_personnel_plan.json` | `development_personnel.pptx` |