# PPTX Generator 技術仕様書

## エグゼクティブサマリー

### プロジェクトの目的

PPTX Generator は、PowerPoint テンプレートと資料データを取り込み、企業ブランドに沿った提案書を自動生成する CLI ベースのツールです。営業・コンサル部門のドキュメント作成負荷を大幅に軽減し、生成物の品質をブランドガイドラインに沿って均一化します。

### 解決する課題

| 課題 | 解決策 |
|------|--------|
| 提案書作成の時間的負荷 | JSON/Markdown からの自動生成により、夜間バッチで翌朝受領可能 |
| ビジュアル品質のばらつき | テンプレートから抽出したブランド設定を自動適用 |
| 複数 OS 環境での運用 | Mac/Linux/Windows で同一フローを提供 |
| 手直し工数の増大 | 自動診断・補正機能により人的介入を最小化 |

### 主要機能

1. **テンプレート抽出・検証**: PowerPoint テンプレートからレイアウト構造とブランド設定を抽出
2. **コンテンツ準備**: AI を活用した資料データの構造化と HITL 承認フロー
3. **自動マッピング**: テンプレートレイアウトへのコンテンツ割り当て
4. **PPTX/PDF 生成**: ブランドスタイルを適用した最終成果物の出力
5. **品質診断・補正**: 余白、フォント、コントラスト、箇条書き階層の自動チェック
6. **監査ログ**: 入力から出力までの全処理を追跡可能

---

## 第1章: システム概要

### 1.1 アーキテクチャ全体像

PPTX Generator は 4 つの主要ステージで構成される自動生成パイプラインです。

```
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: テンプレート準備                                        │
│  ┌─────────────┐                                                 │
│  │ PowerPoint  │──→ 抽出・検証 ──→ jobspec.json                 │
│  │ テンプレート │                   template_spec.json           │
│  └─────────────┘                   layouts.jsonl                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: コンテンツ準備 (HITL)                                   │
│  ┌─────────────┐                                                 │
│  │ 資料データ   │──→ AI 変換 ──→ prepare_card.json              │
│  │ (MD/JSON)   │    └→ HITL 承認                                │
│  └─────────────┘                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: マッピング (HITL + 自動)                                │
│  prepare_card.json + jobspec.json ──→ generate_ready.json       │
│                                       (レイアウト割り当て済み)     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Stage 4: レンダリング                                            │
│  generate_ready.json ──→ proposal.pptx                          │
│                       └→ proposal.pdf (オプション)                │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 動作モード

#### Dynamic Mode（動的生成モード）

資料データから柔軟にスライドを作成するモード。コンテンツの順番や配置を調整しながら何度でも出し直せます。

**ユースケース**:
- 資料の全体構成が未確定の案件
- AI によるコンテンツ生成を活用したい場合
- 章構成を柔軟に変更したい場合

#### Static Mode（静的生成モード）

テンプレートで決めたスライド構造に合わせて資料データを自動割り当てするモード。

**構造階層**:
```
Blueprint（テンプレート全体の設計図）
└─ Slide（スライドごとの枠組み）
    └─ Slot（コンテンツ差し込み枠）
```

**ユースケース**:
- スライド配置やルールが決まっている定型資料
- テンプレート駆動で確実に同じ構成を維持したい場合

### 1.3 技術スタック概要

| カテゴリ | 技術 |
|----------|------|
| 言語 | Python 3.12+ |
| PPTX 操作 | python-pptx |
| LLM 連携 | OpenAI API, Azure OpenAI, Anthropic Claude, AWS Bedrock |
| PDF 変換 | LibreOffice (headless) |
| 仕上げ処理 | .NET 8 SDK + Open XML SDK |
| CLI フレームワーク | Click |
| バリデーション | Pydantic, jsonschema |
| パッケージ管理 | uv |
| CI/CD | GitHub Actions, SonarCloud |

---

## 第2章: 機能要件詳細

### 2.1 入力形式

#### 2.1.1 サポートする入力形式

| 形式 | 用途 | Stage |
|------|------|-------|
| JSON | 構造化されたスライド定義 | Stage 2, 3, 4 |
| JSONC | コメント付き JSON | Stage 2 |
| Markdown | 章立てされた資料テキスト | Stage 2 |
| テキスト | プレーンテキスト資料 | Stage 2 |
| PDF | 既存資料の取り込み | Stage 2 |
| URL | Web ページの取り込み | Stage 2 |
| PPTX | テンプレートファイル | Stage 1 |

#### 2.1.2 JSON 仕様構造

```yaml
meta:
  schema_version: string          # スキーマバージョン
  title: string                   # 提案書タイトル
  client: string                  # クライアント名
  author: string                  # 作成者
  created_at: date                # 作成日
  theme: string                   # 適用テーマ
  locale: string                  # ロケール (ja, en)

auth:
  created_by: string              # 作成者 ID
  department: string              # 部署名

slides:
  - id: string                    # スライド ID
    layout: string                # レイアウト名（テンプレートと一致）
    title: string                 # スライドタイトル
    subtitle: string              # サブタイトル
    notes: string                 # ノート

    bullets:                      # 箇条書き
      - id: string
        text: string
        level: int                # 階層レベル (0-3)
        font:
          size_pt: int
          bold: bool
          italic: bool
          color_hex: string

    tables:                       # 表
      - id: string
        anchor: string            # テンプレート図形名
        columns: [string]
        rows: [[string|number]]
        style:
          header_fill: string
          zebra: bool

    charts:                       # グラフ
      - id: string
        anchor: string
        type: string              # bar, line, pie, area
        categories: [string]
        series:
          - name: string
            values: [number]
            color_hex: string
        options:
          data_labels: bool
          y_axis_format: string

    images:                       # 画像
      - id: string
        anchor: string
        source: string            # ファイルパス
        sizing: string            # fit, fill, crop
        position:
          left_in: float
          top_in: float
          width_in: float
          height_in: float

    textboxes:                    # テキストボックス
      - id: string
        text: string
        anchor: string
        position:
          left_in: float
          top_in: float
          width_in: float
          height_in: float
        font:
          size_pt: int
          color_hex: string
          bold: bool
          italic: bool
        paragraph:
          level: int
          line_spacing_pt: float
          space_before_pt: float
          space_after_pt: float
          align: string           # left, center, right, justify
          left_indent_in: float
          right_indent_in: float
          first_line_indent_in: float

assets:
  fonts: [{ name: string, url: string }]
  images: [{ id: string, url: string }]
```

### 2.2 Stage 別機能仕様

#### 2.2.1 Stage 1: テンプレート準備

**目的**: PowerPoint テンプレートから再利用可能な仕様を抽出し、後続 Stage で利用可能にする

**主要コマンド**: `uv run pptx template <template.pptx>`

**処理フロー**:
1. テンプレート PPTX を読み込み
2. レイアウト構造を解析
3. プレースホルダーとアンカーを抽出
4. ブランド設定（色・フォント）を取得
5. Template AI による usage_tags 推定（オプション）
6. 検証レポート生成

**出力ファイル**:

| ファイル名 | 説明 |
|-----------|------|
| jobspec.json | テンプレート依存のスライド仕様カタログ |
| template_spec.json | テンプレート構造仕様 |
| branding.json | TemplateStyle スナップショット（`pptx template` 出力、参考用） |
| layouts.jsonl | レイアウト構造情報（1行1レイアウト） |
| diagnostics.json | 抽出・検証時の診断結果 |

**Template AI 連携**:
- 環境変数 `PPTX_TEMPLATE_LLM_PROVIDER` で LLM プロバイダを指定
- `config/usage_tags.json` の canonical タグを基に usage_tags を推定
- 推定結果は `diagnostics.json.template_ai` に記録
- `mock` プロバイダ指定時は静的ルールで完結

**検証項目**:
- レイアウト名の重複チェック
- プレースホルダー ID の一意性
- アンカー命名規約の遵守
- 禁止文字・特殊文字の検出

#### 2.2.2 Stage 2: コンテンツ準備

**目的**: 資料データを PrepareCard モデルに整形し、HITL 承認を経て Stage 3 へ渡す

**主要コマンド**: `uv run pptx prepare <source> --mode <dynamic|static>`

**処理フロー**:
1. 入力ソース（Markdown/JSON/PDF/URL）を読み込み
2. ContentImportService でテキスト化・正規化
3. PrepareAIOrchestrator が LLM を呼び出してカード生成
4. 章構成と story_phase を付与
5. 監査ログ・AI ログを出力
6. HITL 承認待ち状態へ

**Dynamic Mode の特徴**:
- テンプレート構造に依存せずカード生成
- AI が章構成を自由に決定
- 柔軟なコンテンツ調整が可能

**Static Mode の特徴**:
- Blueprint の Slot 定義に基づいてカード生成
- `.pptx/extract/prompts/` の雛形を編集可能
- `.pptx/slide_inputs.md` でスライド別入力データを指定
- Slot 充足率を監査ログに記録

**出力ファイル**:

| ファイル名 | 説明 |
|-----------|------|
| prepare_card.json | PrepareCard 配列（メイン成果物） |
| prepare_log.json | 承認・差戻しイベントログ |
| prepare_ai_log.json | LLM との対話ログ |
| ai_generation_meta.json | 生成統計・入力ハッシュ |
| prepare_story_outline.json | 章構成とカード紐付け |
| audit_log.json | Stage 2 監査メタ |

**HITL 承認フロー**:
- カードごとに承認/差戻し/部分承認を記録
- 承認済みカードはロックされ、再生成時も保持
- 差戻し理由は CLI 内蔵のテンプレートコードを利用

**AI レビュー支援**:
- 自動レビューでグレード（A/B/C）を付与
- 改善提案と Auto-fix 案を提示
- Auto-fix の適用/却下をログに記録

#### 2.2.3 Stage 3: マッピング

**目的**: PrepareCard にレイアウトを割り当て、generate_ready.json を生成

**主要コマンド**: `uv run pptx compose <jobspec.json> --prepare-cards <path>`

**処理フロー**:
1. prepare_card.json と jobspec.json を読み込み
2. 章テンプレートに基づいて構成を確定（HITL）
3. Layout AI がカード内容とレイアウトの適合度をスコアリング
4. フォールバック制御（縮約→分割→付録）
5. generate_ready.json へレイアウト情報を確定
6. Analyzer 連携で事前診断を実施

**レイアウト選定プロセス**:

```
PrepareCard (story_phase + intent_tags + media_hint)
         ↓
Layout AI Scoring
         ↓
適合度上位候補を選定
         ↓
ルールベース調整 (同梱の `src/pptx_generator/config/pipeline_rules.json`)
         ↓
フォールバック判定
         ↓
generate_ready.json へ確定
```

**フォールバック戦略**:

| 状況 | 対応 |
|------|------|
| コンテンツ量超過 | 縮約または分割 |
| 適合レイアウト不在 | フォールバック配置 |
| 必須 Slot 未充足 | 警告＋付録スライド追加 |

**出力ファイル**:

| ファイル名 | 説明 |
|-----------|------|
| generate_ready.json | レイアウト割り当て済み描画仕様 |
| generate_ready_meta.json | 章テンプレート適合率・承認統計 |
| draft_review_log.json | HITL 操作履歴 |
| draft_mapping_log.json | レイアウトスコア・フォールバック履歴 |
| fallback_report.json | 重大フォールバック時の詳細 |

#### 2.2.4 Stage 4: レンダリング

**目的**: generate_ready.json から最終成果物（PPTX/PDF）を生成

**主要コマンド**: `uv run pptx gen <generate_ready.json>`

**処理フロー**:
1. generate_ready.json を読み込み
2. テンプレートパスを meta.template_path から解決
3. Renderer が python-pptx でスライドを構築
4. テンプレートスタイルを適用（フォント・色・段落設定）
5. Analyzer で品質診断
6. Refiner で自動補正（オプション）
7. Open XML Polisher で仕上げ（オプション）
8. LibreOffice で PDF 変換（オプション）
9. 監査ログ・分析レポート出力

**Renderer の処理内容**:
- タイトル・本文・箇条書きの描画
- 表・グラフ・画像の配置
- アンカー指定時はテンプレート図形を基準に配置
- プレースホルダーのスタイルを継承
- 段落スタイル（揃え・行間・余白・インデント）を適用

**Analyzer の診断項目**:

| Issue タイプ | 説明 | 重大度 |
|-------------|------|--------|
| margin | スライド余白からの逸脱 | warning |
| grid_misaligned | グリッド 0.125in からのズレ | info |
| font_min | フォントサイズが規定未満 | warning |
| contrast_low | コントラスト不足（WCAG 2.1 AA） | warning |
| bullet_depth | 箇条書きレベル上限超過 | error |
| layout_consistency | 箇条書きインデントジャンプ | warning |

**Refiner の補正内容**:

| Fix タイプ | 説明 |
|-----------|------|
| move | 指定デルタで位置調整 |
| font_raise | 最小フォントサイズまで引き上げ |
| color_adjust | テーマカラーへ置換 |
| bullet_cap | 箇条書きレベルの切り上げ |
| bullet_reindent | 許容範囲へレベル再設定 |

**Open XML Polisher**:
- .NET 8 SDK + Open XML SDK で実装
- `config/polisher-rules.json` でルール管理
- フォント最小値の再確認
- テーマ色未リンクの RGB を Accent カラーへマップ
- 段落間隔の最終調整（フォールバック用）

**LibreOffice PDF 変換**:
- headless モードで PPTX → PDF 変換
- タイムアウト: 120 秒（設定可能）
- リトライ: 2 回（設定可能）
- 変換メトリクスを `audit_log.json.pdf_export_metadata` に記録

**出力ファイル**:

| ファイル名 | 説明 |
|-----------|------|
| proposal.pptx | **最終成果物** PPTX |
| proposal.pdf | **最終成果物** PDF（オプション） |
| analysis.json | Analyzer 解析結果 |
| review_engine_analyzer.json | レビュー用メタ情報 |
| rendering_log.json | レンダリング監査結果 |
| monitoring_report.json | 警告件数サマリ |
| audit_log.json | 生成時刻・成果物ハッシュ |
| analysis_snapshot.json | アンカー構造スナップショット |

### 2.3 バリデーションルール

#### 2.3.1 テキストバリデーション

| 項目 | ルール | 出典 |
|------|--------|------|
| 禁則語 | `config/pipeline_rules.json` の `forbidden_words` リスト | Validator |
| 表記揺れ | 正式名称マッピング辞書で置換 | Validator |
| タイトル文字数 | ≤ 25 文字（推奨） | レイアウト依存 |
| 本文行文字数 | ≤ 40 文字（推奨） | レイアウト依存 |
| 本文行数 | ≤ 6 行（推奨） | レイアウト依存 |

#### 2.3.2 ビジュアルバリデーション

| 項目 | ルール | 基準 |
|------|--------|------|
| スライド余白 | 10.0in × 7.5in | Analyzer |
| グリッドスナップ | 0.125in 単位 | Analyzer |
| 最小フォントサイズ | 設定値以上（既定 10pt） | Analyzer/Refiner |
| コントラスト比 | 4.5:1 以上（大文字は 3.0:1） | WCAG 2.1 AA |
| 箇条書き階層 | 0-3 レベル | Analyzer |
| 画像解像度 | 150dpi 以上推奨 | Validator |

#### 2.3.3 構造バリデーション

| 項目 | ルール |
|------|--------|
| レイアウト名 | テンプレート内に存在すること |
| アンカー名 | テンプレート図形名と一致 |
| スライド ID | ドキュメント内で一意 |
| 必須フィールド | Pydantic モデルで検証 |

---

## 第3章: アーキテクチャ設計

### 3.1 コンポーネント構成

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer (Click)                        │
│  pptx template | prepare | compose | gen                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Handler Layer                               │
│  TemplateHandler | PrepareHandler | ComposeHandler |            │
│  RenderingHandler                                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ TemplateExtractor│  │ PrepareOrchestra │                     │
│  │                  │  │ tor              │                     │
│  └──────────────────┘  └──────────────────┘                     │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ DraftRecommender │  │ Renderer         │                     │
│  │                  │  │                  │                     │
│  └──────────────────┘  └──────────────────┘                     │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Analyzer         │  │ Refiner          │                     │
│  │                  │  │                  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      AI Services                                 │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Template AI      │  │ Prepare AI       │                     │
│  │                  │  │                  │                     │
│  └──────────────────┘  └──────────────────┘                     │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Layout AI        │  │ Slide AI         │                     │
│  │                  │  │                  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      External Services                           │
│  OpenAI API | Azure OpenAI | Anthropic Claude | AWS Bedrock     │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 データモデル階層

```
┌─────────────────────────────────────────────────────────────────┐
│                      入力レイヤ                                   │
│  PrepareSource (Markdown/JSON/PDF/URL)                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      正規化レイヤ                                 │
│  PrepareDocument                                                 │
│    └─ PrepareCard[]                                             │
│         ├─ card_id                                              │
│         ├─ role (story_phase, intent_tags, media_hint)         │
│         ├─ content (title, headline, body[], notes[])          │
│         └─ meta                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      マッピングレイヤ                             │
│  GenerateReady                                                   │
│    ├─ meta (template_path, template_style)                      │
│    └─ slides[]                                                  │
│         ├─ id, layout                                           │
│         ├─ title, subtitle, notes                               │
│         ├─ bullets[] (確定済み配置)                              │
│         ├─ tables[] (アンカー割り当て済み)                        │
│         ├─ charts[] (アンカー割り当て済み)                        │
│         ├─ images[] (アンカー割り当て済み)                        │
│         └─ textboxes[] (段落スタイル確定)                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      レンダリングレイヤ                           │
│  python-pptx Presentation オブジェクト                           │
│    └─ Slide[]                                                   │
│         ├─ Shapes[]                                             │
│         │    ├─ Placeholder                                     │
│         │    ├─ TextBox                                         │
│         │    ├─ Table                                           │
│         │    ├─ Chart                                           │
│         │    └─ Picture                                         │
│         └─ Notes                                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      出力レイヤ                                   │
│  proposal.pptx / proposal.pdf                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 AI サービス統合

#### 3.3.1 対応 LLM プロバイダ

| プロバイダ | 環境変数 | 対応 Stage |
|-----------|---------|-----------|
| OpenAI | `OPENAI_API_KEY` | Stage 1, 2, 3 |
| Azure OpenAI | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY` | Stage 1, 2, 3 |
| Anthropic Claude | `ANTHROPIC_API_KEY` | Stage 1, 2, 3 |
| AWS Bedrock (Claude) | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Stage 1, 2, 3 |
| Mock | `PPTX_LLM_PROVIDER=mock` | 全 Stage（テスト用） |

#### 3.3.2 AI サービス別責務

| サービス | 役割 | Stage |
|---------|------|-------|
| Template AI | レイアウトの usage_tags 推定 | Stage 1 |
| Prepare AI | 資料データから PrepareCard 生成 | Stage 2 |
| Slide AI | カード内容の最適化・再構成 | Stage 2 |
| Layout AI | カードとレイアウトの適合度スコアリング | Stage 3 |

#### 3.3.3 プロンプト管理

```
config/
├── template_ai_policies.json  # Template AI のプロンプト・モデル設定
├── slide_ai_policies.json     # Slide AI のポリシー定義
├── layout_ai_policies.json    # Layout AI のスコアリングルール
└── usage_tags.json            # canonical タグ定義とシノニム
```

### 3.4 ストレージ構成

```
プロジェクトルート/
├── .pptx/
│   ├── extract/                # Stage 1 出力
│   │   ├── jobspec.json
│   │   ├── template_spec.json
│   │   ├── branding.json       # TemplateStyle スナップショット（参考）
│   │   ├── layouts.jsonl
│   │   ├── diagnostics.json
│   │   └── prompts/           # Static mode 用雛形
│   ├── prepare/               # Stage 2 出力
│   │   ├── prepare_card.json
│   │   ├── prepare_log.json
│   │   ├── prepare_ai_log.json
│   │   ├── ai_generation_meta.json
│   │   ├── prepare_story_outline.json
│   │   └── audit_log.json
│   ├── draft/                 # Stage 3 中間成果物
│   │   ├── store/             # HITL 承認データ
│   │   └── ...
│   ├── compose/               # Stage 3 出力
│   │   ├── generate_ready.json
│   │   ├── generate_ready_meta.json
│   │   ├── draft_review_log.json
│   │   ├── draft_mapping_log.json
│   │   └── fallback_report.json
│   ├── gen/                   # Stage 4 出力
│   │   ├── proposal.pptx      # 最終成果物
│   │   ├── proposal.pdf       # 最終成果物（オプション）
│   │   ├── analysis.json
│   │   ├── rendering_log.json
│   │   ├── monitoring_report.json
│   │   └── audit_log.json
│   └── validation/            # 検証成果物
├── samples/
│   ├── templates/             # サンプルテンプレート
│   │   └── templates.pptx
│   ├── contents/              # サンプル資料データ
│   └── json/                  # サンプル JSON
├── config/                    # 設定ファイル
└── templates/                 # 本番テンプレート管理
    └── libraries/
        └── <brand>/<version>/
```

---

## 第4章: CLI コマンドリファレンス

### 4.1 Stage 1 コマンド

#### `pptx template`

テンプレート抽出・検証を一括実行

```bash
uv run pptx template <template.pptx> \
  [--output <dir>] \
  [--layout <keyword>] \
  [--anchor <keyword>] \
  [--format <json|yaml>] \
  [--mode <dynamic|static>] \
  [--with-release] \
  [--brand <name>] \
  [--version <value>]
```

**主要オプション**:

| オプション | 説明 | 既定値 |
|-----------|------|--------|
| `--output` | 抽出結果の出力先 | `.pptx/extract` |
| `--mode` | 運用モード（dynamic/static） | `dynamic` |
| `--with-release` | リリースメタを生成 | 無効 |
| `--brand` | ブランド名（--with-release 時） | - |
| `--version` | テンプレートバージョン | - |

**使用例**:
```bash
# 基本的な抽出
uv run pptx template samples/templates/templates.pptx

# Static モードで抽出＋リリースメタ生成
uv run pptx template samples/templates/templates.pptx \
  --mode static \
  --with-release \
  --brand corporate \
  --version 1.0
```

#### `pptx tpl-extract`

抽出のみを実行（検証は別途実施）

```bash
uv run pptx tpl-extract \
  --template <path> \
  [--output <dir>] \
  [--layout <keyword>] \
  [--anchor <keyword>]
```

#### `pptx layout-validate`

レイアウト検証を単独実行

```bash
uv run pptx layout-validate \
  --template <path> \
  [--output <dir>] \
  [--baseline <layouts.jsonl>] \
  [--analyzer-snapshot <path>]
```

#### `pptx tpl-release`

リリースメタ生成を単独実行

```bash
uv run pptx tpl-release \
  --template <path> \
  --brand <name> \
  --version <value> \
  [--baseline-release <path>] \
  [--golden-spec <spec.json>...]
```

### 4.2 Stage 2 コマンド

#### `pptx prepare`

コンテンツ準備を実行

```bash
uv run pptx prepare <prepare_source...> \
  --mode <dynamic|static> \
  [--output <dir>] \
  [--jobspec <path>] \
  [-p/--page-limit <int>]
```

**主要オプション**:

| オプション | 説明 | 既定値 |
|-----------|------|--------|
| `--mode` | 生成モード（dynamic/static） | 必須 |
| `--output` | 成果物の出力先 | `.pptx/prepare` |
| `--jobspec` | jobspec.json のパス（static 時） | 自動探索 |
| `-p/--page-limit` | 生成カード枚数上限 | 制限なし |

**使用例**:
```bash
# Dynamic モードでMarkdownから生成
uv run pptx prepare samples/input/pitch.md \
  --mode dynamic

# Static モードで複数ソースから生成
uv run pptx prepare notes/brief.md https://example.com/report.pdf \
  --mode static \
  --jobspec .pptx/extract/jobspec.json

# カード枚数を制限
uv run pptx prepare samples/input/pitch.md \
  --mode dynamic \
  -p 10
```

### 4.3 Stage 3 コマンド

#### `pptx compose`

マッピング全体を一括実行（推奨）

```bash
uv run pptx compose <jobspec.json> \
  [--prepare-cards <path>] \
  [--rules <path>] \
  [--show-layout-reasons]
```

**主要オプション**:

| オプション | 説明 | 既定値 |
|-----------|------|--------|
| `--prepare-cards` | prepare_card.json のパス | `.pptx/prepare/prepare_card.json` |
| `--output, -o <dir>` | `generate_ready.json` などの出力先 | `.pptx/compose` |
| （自動） | ドラフト成果物の出力先 | `<output>/draft` |
| `--rules` | マッピングルール設定 | `src/pptx_generator/config/pipeline_rules.json` |
| `--show-layout-reasons` | スコア内訳を表示 | 無効 |

**使用例**:
```bash
# 基本的なマッピング
uv run pptx compose .pptx/extract/jobspec.json \
  --prepare-cards .pptx/prepare/prepare_card.json

# スコア内訳を確認しながら実行
uv run pptx compose .pptx/extract/jobspec.json \
  --show-layout-reasons
```

#### `pptx outline`

章構成確認（HITL）のみ実行

```bash
uv run pptx outline <jobspec.json> \
  --prepare-cards <path> \
  [--output <dir>]
```

#### `pptx mapping`

レイアウト割り当てのみ実行

```bash
uv run pptx mapping <jobspec.json> \
  --prepare-cards <path> \
  [--output <dir>] \
  [--rules <path>]
```

### 4.4 Stage 4 コマンド

#### `pptx gen`

レンダリングと成果物生成

```bash
uv run pptx gen <generate_ready.json> \
  [--output <dir>] \
  [--pptx-name <filename>] \
  [--rules <path>] \
  [--export-pdf] \
  [--pdf-mode <both|only>] \
  [--polisher/--no-polisher] \
  [--emit-structure-snapshot]
```

**主要オプション**:

| オプション | 説明 | 既定値 |
|-----------|------|--------|
| `--output` | 生成物の出力先 | `.pptx/gen` |
| `--pptx-name` | 出力 PPTX ファイル名 | `proposal.pptx` |
| `--export-pdf` | PDF を同時生成 | 無効 |
| `--pdf-mode` | PDF のみ出力するか | `both` |
| `--polisher/--no-polisher` | Polisher 実行 | ルール設定準拠 |
| `--polisher-path` | Polisher 実行ファイルパス | 設定ファイル/環境変数 |
| `--libreoffice-path` | soffice のパス | PATH から探索 |
| `--pdf-timeout` | PDF 変換タイムアウト（秒） | 120 |
| `--pdf-retries` | PDF 変換リトライ回数 | 2 |
| `--emit-structure-snapshot` | 構造スナップショット出力 | 無効 |

**使用例**:
```bash
# 基本的な生成
uv run pptx gen .pptx/compose/generate_ready.json

# PDF も同時生成
uv run pptx gen .pptx/compose/generate_ready.json \
  --export-pdf

# Polisher を無効化
uv run pptx gen .pptx/compose/generate_ready.json \
  --no-polisher

# 構造スナップショットを出力
uv run pptx gen .pptx/compose/generate_ready.json \
  --emit-structure-snapshot
```

### 4.5 ログレベル制御

環境変数またはオプションでログレベルを制御:

```bash
# 環境変数で制御
export LOG_LEVEL=debug
uv run pptx gen .pptx/compose/generate_ready.json

# オプションで制御
uv run pptx gen .pptx/compose/generate_ready.json --verbose
uv run pptx gen .pptx/compose/generate_ready.json --debug
```

---

## 第5章: テンプレート設計ガイド

### 5.1 テンプレート構造

#### 5.1.1 基本構成要素

```
PowerPoint テンプレート (.pptx)
├── スライドマスター
│   ├── テーマ設定（色・フォント）
│   └── レイアウト[]
│       ├── レイアウト名（JSON の layout と一致）
│       ├── プレースホルダー[]
│       │   └── 名前（アンカーとして利用）
│       └── 図形[]
│           └── 名前（アンカーとして利用）
└── サンプルスライド（削除推奨）
```

#### 5.1.2 レイアウト命名規約

| レイアウト名 | 用途 | 主なアンカー例 |
|-------------|------|---------------|
| `Title` | カバースライド | `cover-visual`, `brand-logo` |
| `Agenda` | アジェンダ一覧 | `milestone-table`, `agenda-visual` |
| `Two Column Detail` | 2 カラム詳細説明 | `detail-visual` |
| `One Column Detail` | 1 カラム詳細説明 | `detail-visual` |
| `Closing` | クロージング＋CTA | `closing-cta` |
| `Timeline Detail` | タイムライン | `Timeline Track`, `Timeline Notes` |
| `Comparison Two Axis` | 2 軸比較 | `Axis Left`, `Axis Right` |
| `Fact Sheet` | KPI サマリー | `Fact Summary` |

#### 5.1.3 アンカー命名規約

**推奨形式**: `<用途>-<種類>`

**例**:
- `brand-logo`: ブランドロゴ
- `cover-visual`: カバー画像
- `detail-visual`: 詳細説明用画像
- `metric-chart`: メトリクスグラフ
- `timeline-table`: タイムライン表
- `closing-cta`: クロージングCTA

**注意事項**:
- 同一レイアウト内では一意にすること
- 日本語も使用可能だが、JSON との完全一致が必要
- プレースホルダーを優先的に利用
- 図形を利用する場合は透明にしておく

### 5.2 テンプレート準備チェックリスト

#### Phase 1: 設計

- [ ] 想定ストーリー（タイトル、アジェンダ、セクション、まとめ）を整理
- [ ] 必要なレイアウトパターンを洗い出し
- [ ] 各レイアウトで必要なアンカーを定義
- [ ] ブランドカラー・フォントを確認

#### Phase 2: 作成

- [ ] PowerPoint でスライドマスターを編集
- [ ] テーマ設定（配色・フォント）を適用
- [ ] レイアウトごとにプレースホルダー配置
- [ ] 差し込み対象の図形に一意な名前を設定
- [ ] 不要なサンプルスライドを削除
- [ ] `.pptx` 形式で保存（.potx は未対応）

#### Phase 3: 検証

- [ ] `uv run pptx template <template.pptx>` で抽出
- [ ] `diagnostics.json` でエラー・警告を確認
- [ ] `layouts.jsonl` でレイアウト一覧を確認
- [ ] サンプル JSON でレンダリングテスト
- [ ] LibreOffice で開いて互換性確認

### 5.3 テンプレート更新フロー

```
1. テンプレート編集
   ↓
2. 抽出・検証
   uv run pptx template templates/.../template.pptx \
     --baseline-release releases/.../template_release.json
   ↓
3. 差分レポート確認
   .pptx/extract/diagnostics.json
   .pptx/extract/diff_report.json
   ↓
4. ゴールデンサンプルテスト
   uv run pptx tpl-release ... \
     --golden-spec samples/json/sample_spec.json
   ↓
5. リリース
   templates/releases/<brand>/<version>/ へアーカイブ
```

### 5.4 サンプルテンプレート

プロジェクトに `samples/templates/templates.pptx` を同梱しています。

**カバレッジ**: 50 ページ規模

**カテゴリ別レイアウト**:
- セクション区切り: 3 パターン
- ビジネスサマリー: 5 パターン
- タイムライン: 3 パターン
- KPI: 4 パターン
- 財務: 3 パターン
- 組織: 3 パターン
- プロセス: 5 パターン
- リスク: 3 パターン
- データビジュアル: 8 パターン
- クロージング: 3 パターン

---

## 第6章: データフロー詳細

### 6.1 Stage 別入出力マトリクス

| ファイル名 | 必須 | 概要 | 生成 Stage | 参照 Stage |
|-----------|------|------|-----------|-----------|
| template.pptx | ✅ | テンプレート本体 | ユーザー準備 | S1, S3, S4 |
| jobspec.json | ✅ | テンプレート仕様カタログ | S1 | S2, S3, S4 |
| template_spec.json | ○ | テンプレート構造仕様 | S1 | S3 |
| branding.json | ○ | TemplateStyle スナップショット（`pptx template` 出力、参考） | S1 | - |
| layouts.jsonl | ○ | レイアウト構造（1行1件） | S1 | S3 |
| diagnostics.json | ○ | 抽出・検証診断結果 | S1 | - |
| template_release.json | ○ | リリースメタ | S1 | S1（差分比較） |
| release_report.json | ○ | 差分レポート | S1 | - |
| golden_runs.json | ○ | ゴールデンテスト結果 | S1 | - |
| prepare_card.json | ✅ | PrepareCard 配列 | S2 | S3 |
| prepare_log.json | ○ | 承認・差戻しログ | S2 | S3 |
| prepare_ai_log.json | ○ | LLM 対話ログ | S2 | S3 |
| ai_generation_meta.json | ○ | 生成統計 | S2 | S3 |
| prepare_story_outline.json | ○ | 章構成 | S2 | S3 |
| prepare/audit_log.json | ○ | Stage 2 監査ログ | S2 | - |
| generate_ready.json | ✅ | レイアウト割り当て済み仕様 | S3 | S4 |
| generate_ready_meta.json | ✅ | 章適合率・承認統計 | S3 | S4 |
| draft_review_log.json | ○ | HITL 操作履歴 | S3 | - |
| draft_mapping_log.json | ○ | レイアウトスコア履歴 | S3 | - |
| fallback_report.json | ○ | フォールバック詳細 | S3 | - |
| proposal.pptx | ✅ | **最終成果物** PPTX | S4 | - |
| proposal.pdf | ○ | **最終成果物** PDF | S4 | - |
| analysis.json | ○ | Analyzer 解析結果 | S4 | - |
| rendering_log.json | ○ | レンダリング監査結果 | S4 | - |
| monitoring_report.json | ○ | 警告件数サマリ | S4 | - |
| gen/audit_log.json | ○ | Stage 4 監査ログ | S4 | - |
| analysis_snapshot.json | ○ | 構造スナップショット | S4 | S1（比較） |

### 6.2 PrepareCard データ構造

```json
{
  "card_id": "card_001",
  "order": 1,
  "role": {
    "story_phase": "opening",
    "intent_tags": ["title", "agenda"],
    "media_hint": "visual"
  },
  "content": {
    "title": "プロジェクト概要",
    "headline": "デジタル変革による業務効率化",
    "body": [
      {
        "text": "現状の課題分析",
        "level": 0
      },
      {
        "text": "システム導入による効果",
        "level": 1
      }
    ],
    "notes": [
      "補足説明をノート欄に記載"
    ]
  },
  "meta": {
    "generated_at": "2025-01-15T10:30:00Z",
    "content_hash": "abc123...",
    "source_line_range": [1, 20]
  }
}
```

**主要フィールド**:

| フィールド | 説明 | データ型 |
|-----------|------|---------|
| card_id | カード一意識別子 | string |
| order | カード順序 | integer |
| role.story_phase | 章フェーズ（opening/body/closing） | string |
| role.intent_tags | スライド意図タグ（title/content/cta 等） | string[] |
| role.media_hint | メディアヒント（visual/chart/table） | string |
| content.title | スライドタイトル | string |
| content.headline | ヘッドライン | string |
| content.body[] | 本文（箇条書き） | object[] |
| content.notes[] | ノート | string[] |
| meta.content_hash | コンテンツハッシュ（差分検出用） | string |

### 6.3 generate_ready.json 構造

```json
{
  "meta": {
    "schema_version": "generate-ready-v1",
    "title": "デジタル変革提案書",
    "template_path": "samples/templates/templates.pptx",
    "template_style": {
      "fonts": {
        "heading": { "name": "Arial", "size_pt": 28, "bold": true },
        "body": { "name": "Arial", "size_pt": 14 }
      },
      "colors": {
        "primary": "#1E3A8A",
        "accent": "#3B82F6"
      }
    }
  },
  "slides": [
    {
      "id": "slide_001",
      "layout": "Title",
      "title": "プロジェクト概要",
      "subtitle": "デジタル変革による業務効率化",
      "bullets": [],
      "images": [
        {
          "id": "img_001",
          "anchor": "cover-visual",
          "source": "assets/cover.png",
          "sizing": "fit"
        }
      ]
    }
  ]
}
```

**meta フィールド詳細**:

| フィールド | 説明 | 必須 |
|-----------|------|------|
| schema_version | スキーマバージョン | ✅ |
| title | 提案書タイトル | ✅ |
| template_path | テンプレートパス（相対 or 絶対） | ✅ |
| template_style | テンプレートから抽出したスタイル | ✅ |

### 6.4 監査ログ構造

#### Stage 2: prepare/audit_log.json

```json
{
  "stage": "prepare",
  "generated_at": "2025-01-15T10:30:00Z",
  "policy_id": "prepare_policy_v1",
  "output_files": {
    "prepare_card": ".pptx/prepare/prepare_card.json",
    "prepare_log": ".pptx/prepare/prepare_log.json",
    "ai_log": ".pptx/prepare/prepare_ai_log.json"
  },
  "statistics": {
    "total_cards": 15,
    "story_phases": {
      "opening": 2,
      "body": 11,
      "closing": 2
    }
  },
  "prepare_normalization": {
    "import_sources": [
      {
        "path": "samples/input/pitch.md",
        "format": "markdown",
        "size_bytes": 2048
      }
    ]
  }
}
```

#### Stage 4: gen/audit_log.json

```json
{
  "stage": "rendering",
  "generated_at": "2025-01-15T11:00:00Z",
  "input_hash": "sha256:abc123...",
  "output_files": {
    "pptx": ".pptx/gen/proposal.pptx",
    "pdf": ".pptx/gen/proposal.pdf"
  },
  "rendering_metrics": {
    "total_slides": 15,
    "processing_time_sec": 12.5,
    "warnings": 3,
    "errors": 0
  },
  "pdf_export_metadata": {
    "success": true,
    "conversion_time_sec": 8.2,
    "libreoffice_version": "7.6.4.1",
    "exit_code": 0
  },
  "refiner_adjustments": [
    {
      "slide_id": "slide_005",
      "shape_id": "bullet_box",
      "adjustment": "bullet_reindent",
      "before": { "level": 4 },
      "after": { "level": 3 }
    }
  ]
}
```

---

## 第7章: 環境構築・運用

### 7.1 環境要件

#### 7.1.1 必須要件

| コンポーネント | バージョン | 用途 |
|--------------|-----------|------|
| Python | 3.12+ | メイン実行環境 |
| uv | 最新版 | パッケージ管理 |

#### 7.1.2 オプション要件

| コンポーネント | バージョン | 用途 |
|--------------|-----------|------|
| .NET SDK | 8.0+ | Open XML Polisher 実行 |
| LibreOffice | 7.4+ | PDF 変換 |

#### 7.1.3 LLM API 要件（いずれか）

| プロバイダ | 必要な環境変数 |
|-----------|---------------|
| OpenAI | `OPENAI_API_KEY` |
| Azure OpenAI | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY` |
| Anthropic Claude | `ANTHROPIC_API_KEY` |
| AWS Bedrock | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Mock（テスト用） | `PPTX_LLM_PROVIDER=mock` |

### 7.2 セットアップ手順

#### Step 1: リポジトリクローン

```bash
git clone https://github.com/yurake/pptx_generator.git
cd pptx_generator
```

#### Step 2: Python 環境構築

```bash
# Python 3.12 仮想環境を作成
python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# uv で依存関係を同期
uv sync
```

#### Step 3: LLM API 設定

```bash
# OpenAI を使用する場合
export OPENAI_API_KEY="sk-..."

# Azure OpenAI を使用する場合
export AZURE_OPENAI_ENDPOINT="https://..."
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
export AZURE_OPENAI_API_KEY="..."

# Anthropic Claude を使用する場合
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Step 4: オプションツールのインストール

**LibreOffice（PDF 変換用）**:
```bash
# macOS
brew install libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# Windows
# 公式サイトからインストーラーをダウンロード
```

**.NET SDK（Polisher 用）**:
```bash
# macOS
brew install dotnet-sdk

# Ubuntu/Debian
sudo apt-get install dotnet-sdk-8.0

# Windows
# 公式サイトからインストーラーをダウンロード
```

#### Step 5: 動作確認

```bash
# CLI が利用可能か確認
uv run pptx --help

# サンプル実行
uv run pptx template samples/templates/templates.pptx
uv run pptx prepare samples/input/pitch.md --mode dynamic
```

### 7.3 設定ファイル

#### src/pptx_generator/config/pipeline_rules.json

```json
{
  "forbidden_words": [
    "禁止ワード1",
    "禁止ワード2"
  ],
  "analyzer": {
    "min_font_size": 10,
    "default_font_size": 14,
    "default_font_color": "#000000",
    "preferred_text_color": "#1E3A8A",
    "background_color": "#FFFFFF",
    "min_contrast_ratio": 4.5,
    "large_text_min_contrast": 3.0,
    "large_text_threshold_pt": 18,
    "margin_in": 0.5,
    "slide_width_in": 10.0,
    "slide_height_in": 7.5
  },
  "refiner": {
    "enable_bullet_reindent": true,
    "enable_font_raise": true,
    "min_font_size": 10,
    "enable_color_adjust": false,
    "preferred_text_color": "#1E3A8A",
    "fallback_font_color": "#000000"
  },
  "polisher": {
    "enabled": true,
    "executable": "dotnet/OpenXmlPolish/bin/Release/net8.0/OpenXmlPolish.dll",
    "rules_path": "config/polisher-rules.json",
    "timeout_sec": 60
  }
}
```

#### config/usage_tags.json

```json
{
  "version": "2.0",
  "intents": {
    "title": {
      "description": "タイトル・カバースライド",
      "synonyms": ["cover", "headline"],
      "examples": ["プロジェクト概要", "提案書表紙"]
    },
    "agenda": {
      "description": "アジェンダ・目次",
      "synonyms": ["toc", "contents"],
      "examples": ["本日の議題", "プレゼンテーション構成"]
    },
    "content": {
      "description": "コンテンツ・本文",
      "synonyms": ["body", "detail"],
      "examples": ["現状分析", "ソリューション提案"]
    },
    "closing": {
      "description": "まとめ・クロージング",
      "synonyms": ["summary", "conclusion"],
      "examples": ["次のステップ", "まとめ"]
    }
  },
  "media": {
    "visual": {
      "description": "画像・ビジュアル重視",
      "synonyms": ["image", "photo"],
      "examples": ["カバー画像", "製品写真"]
    },
    "chart": {
      "description": "グラフ・チャート",
      "synonyms": ["graph", "plot"],
      "examples": ["売上推移", "市場シェア"]
    },
    "table": {
      "description": "表・データ",
      "synonyms": ["grid", "data"],
      "examples": ["比較表", "スケジュール"]
    }
  }
}
```

### 7.4 運用上の注意事項

#### 7.4.1 環境変数の優先順位

1. コマンドラインオプション
2. 環境変数
3. `config/*.json` の設定
4. デフォルト値

#### 7.4.2 ログレベル制御

| 環境変数 | 効果 |
|---------|------|
| `LOG_LEVEL=debug` | 詳細なデバッグログ |
| `LOG_LEVEL=info` | 通常の情報ログ |
| `LOG_LEVEL=warning` | 警告以上のみ |
| `LOG_LEVEL=error` | エラーのみ |

#### 7.4.3 キャッシュディレクトリ

```bash
# uv のキャッシュディレクトリを指定
export UV_CACHE_DIR=.uv-cache
```

#### 7.4.4 並列実行時の注意

- `.pptx/` 配下のディレクトリはプロセスごとに分離推奨
- `--output` オプションで出力先を明示的に分ける
- 同一テンプレートへの同時アクセスは問題なし（読み取り専用）

---

## 第8章: テスト戦略

### 8.1 テスト階層

| レベル | 対象 | ツール | カバレッジ目標 |
|--------|------|--------|--------------|
| 単体テスト | 関数・クラス単位 | pytest | 80%+ |
| 統合テスト | CLI エンドツーエンド | pytest | 主要フロー網羅 |
| システムテスト | Stage 1-4 通し | 手動 + pytest | 代表シナリオ |
| パフォーマンステスト | 30 スライド規模 | 計測スクリプト | 1 分以内 |
| セキュリティテスト | 脆弱性スキャン | pip-audit, SonarCloud | 重大な問題ゼロ |

### 8.2 テスト実行

#### 全テスト実行

```bash
uv run --extra dev pytest
```

#### カバレッジレポート生成

```bash
uv run --extra dev pytest --cov=src --cov-report=xml
```

#### 差分カバレッジ確認

```bash
uv tool run diff-cover coverage.xml --compare-branch origin/main
```

#### 統合テスト

```bash
uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py
```

### 8.3 テストデータ

```
tests/
├── fixtures/              # テストフィクスチャ
│   ├── templates/         # テスト用テンプレート
│   ├── contents/          # テスト用資料データ
│   └── json/              # テスト用 JSON
├── integration/           # 統合テスト
├── unit/                  # 単体テスト
└── AGENTS.md             # テスト戦略詳細
```

### 8.4 Golden Sample テスト

**目的**: テンプレート更新時の互換性検証

**フロー**:
1. `--golden-spec` で既知の JSON 仕様を指定
2. レンダリング → Analyzer → LibreOffice まで実行
3. 成功/失敗を `golden_runs.json` に記録
4. エラー時は差分レポートを生成

**実行例**:
```bash
uv run pptx tpl-release \
  --template samples/templates/templates.pptx \
  --brand corporate \
  --version 1.1 \
  --golden-spec samples/json/sample_spec_01.json \
  --golden-spec samples/json/sample_spec_02.json
```

---

## 第9章: セキュリティ・コンプライアンス

### 9.1 セキュリティ設計

#### 9.1.1 データ保護

| 対象 | 対策 |
|------|------|
| 入力データ | ファイルシステムレベルの権限制御 |
| LLM 通信 | HTTPS 通信、プロンプト/レスポンスの監査ログ記録 |
| 機密情報 | 匿名化・マスキング処理 |
| 成果物 | ストレージ保存時の暗号化（SSE） |

#### 9.1.2 認証・認可

**CLI 実行時**:
- PAT (Personal Access Token) または SAS トークン
- 環境変数での管理推奨

**API 実行時（将来拡張）**:
- Azure AD / OAuth2
- RBAC によるアクセス制御

#### 9.1.3 脆弱性管理

**定期スキャン**:
```bash
# Python パッケージ
pip-audit

# .NET パッケージ
dotnet list package --vulnerable
```

**CI での自動実行**:
- GitHub Actions で毎回実行
- 重大な脆弱性検出時は PR ブロック

**Dependabot / Renovate**:
- 週次で依存パッケージ更新チェック
- 自動 PR 作成

### 9.2 監査ログ

#### 9.2.1 記録項目

| 項目 | 説明 |
|------|------|
| 実行時刻 | ISO 8601 形式のタイムスタンプ |
| ユーザー ID | 実行者の識別子 |
| 操作内容 | 実行した CLI コマンド |
| 入力ファイル | 入力パスとハッシュ値 |
| 出力ファイル | 成果物パスとハッシュ値 |
| LLM 呼び出し | プロンプト・レスポンス・トークン数 |
| エラー情報 | 例外内容とスタックトレース |

#### 9.2.2 保持期間

| ログ種別 | 保持期間 | 保存場所 |
|---------|---------|---------|
| 監査ログ | 90 日（設定可能） | `.pptx/**/audit_log.json` |
| AI ログ | 90 日 | `.pptx/**/prepare_ai_log.json` |
| 成果物 | 90 日 | `.pptx/gen/` |

### 9.3 コンプライアンス

#### 9.3.1 ライセンス管理

**プロジェクトライセンス**: MIT License

**主要依存ライブラリ**:
- python-pptx: MIT
- Pydantic: MIT
- Click: BSD
- OpenAI Python SDK: MIT
- FastAPI: MIT

#### 9.3.2 データプライバシー

**取り扱う個人情報**:
- なし（ビジネスドキュメントのみ）

**外部送信データ**:
- LLM API: 資料テキスト（匿名化推奨）
- 記録: `prepare_ai_log.json` にプロンプト全文を保存

**GDPR 対応**:
- EU ユーザーからの要求があれば検討

---

## 第10章: パフォーマンス・スケーラビリティ

### 10.1 パフォーマンス目標

| 指標 | 目標値 | 測定方法 |
|------|--------|---------|
| 30 スライド生成 | 1 分以内 | end-to-end 計測 |
| テンプレート抽出 | 30 秒以内 | `pptx template` 実行時間 |
| PDF 変換 | 10 秒以内 | LibreOffice 実行時間 |
| LLM レスポンス | 3 秒以内/カード | `prepare_ai_log.json` の記録 |

### 10.2 ボトルネック分析

#### Stage 別処理時間の目安

| Stage | 処理内容 | 目安時間（30 スライド） |
|-------|---------|----------------------|
| Stage 1 | テンプレート抽出 | 20 秒 |
| Stage 2 | コンテンツ準備（LLM 利用） | 45 秒 |
| Stage 3 | マッピング | 10 秒 |
| Stage 4 | レンダリング | 15 秒 |
| PDF 変換 | LibreOffice | 8 秒 |
| Polisher | .NET 処理 | 5 秒 |

**合計**: 約 103 秒（目標 120 秒以内）

#### 最適化ポイント

| 対象 | 施策 |
|------|------|
| LLM 呼び出し | バッチリクエスト、並列実行 |
| テンプレート読み込み | キャッシュ活用 |
| PDF 変換 | タイムアウト設定、リトライ制御 |
| Analyzer | 対象図形の絞り込み |

### 10.3 スケーラビリティ

#### 水平スケーリング

**バッチ処理モード**:
```bash
# 複数 JSON を並列処理
for spec in specs/*.json; do
  uv run pptx gen "$spec" --output "outputs/$(basename $spec .json)" &
done
wait
```

**分散実行（将来拡張）**:
- Azure Functions / AWS Lambda での並列実行
- キューベース（Azure Queue / AWS SQS）でジョブ管理

#### 垂直スケーリング

**リソース要件**:
- CPU: 2 コア以上推奨
- メモリ: 4GB 以上推奨
- ストレージ: 1GB 以上の空き容量

---

## 第11章: トラブルシューティング

### 11.1 よくあるエラー

#### エラー: `FileNotFoundError: template.pptx`

**原因**: テンプレートパスが不正

**対処**:
```bash
# 相対パスで指定
uv run pptx template samples/templates/templates.pptx

# 絶対パスで指定
uv run pptx template /path/to/template.pptx
```

#### エラー: `TemplateExtractionError: Layout 'XXX' not found`

**原因**: JSON の `layout` フィールドがテンプレートに存在しない

**対処**:
1. `layouts.jsonl` で利用可能なレイアウト名を確認
2. JSON の `layout` を修正

#### エラー: `PrepareAIError: LLM API call failed`

**原因**: LLM API キーが未設定または無効

**対処**:
```bash
# OpenAI の場合
export OPENAI_API_KEY="sk-..."

# Mock プロバイダで動作確認
export PPTX_LLM_PROVIDER=mock
uv run pptx prepare samples/input/pitch.md --mode dynamic
```

#### エラー: `PDFExportError: LibreOffice not found`

**原因**: LibreOffice がインストールされていないか、PATH に含まれていない

**対処**:
```bash
# LibreOffice をインストール
brew install libreoffice  # macOS

# パスを明示指定
uv run pptx gen .pptx/compose/generate_ready.json \
  --export-pdf \
  --libreoffice-path /Applications/LibreOffice.app/Contents/MacOS/soffice
```

#### エラー: `PolisherError: .NET SDK not found`

**原因**: .NET SDK がインストールされていない

**対処**:
```bash
# .NET SDK をインストール
brew install dotnet-sdk  # macOS

# Polisher を無効化して実行
uv run pptx gen .pptx/compose/generate_ready.json --no-polisher
```

### 11.2 デバッグ手法

#### ログレベル引き上げ

```bash
# DEBUG ログを有効化
export LOG_LEVEL=debug
uv run pptx gen .pptx/compose/generate_ready.json --debug
```

#### 中間ファイル確認

```bash
# Stage 別の出力を確認
ls -la .pptx/extract/     # Stage 1
ls -la .pptx/prepare/     # Stage 2
ls -la .pptx/compose/     # Stage 3
ls -la .pptx/gen/         # Stage 4
```

#### 診断レポート確認

```bash
# diagnostics.json を確認
cat .pptx/extract/diagnostics.json | jq '.errors'

# analysis.json を確認
cat .pptx/gen/analysis.json | jq '.issues[] | select(.severity=="error")'
```

### 11.3 サポート連絡先

**GitHub Issues**:
https://github.com/yurake/pptx_generator/issues

**ドキュメント**:
- `docs/runbooks/`: 運用手順書
- `docs/policies/`: ポリシードキュメント
- `tests/AGENTS.md`: テスト戦略

---

## 第12章: 拡張・カスタマイズ

### 12.1 カスタムレイアウトの追加

#### Step 1: テンプレート編集

1. PowerPoint でテンプレートを開く
2. スライドマスターにレイアウトを追加
3. プレースホルダー・図形を配置し、アンカー名を設定
4. 保存

#### Step 2: 抽出・検証

```bash
uv run pptx template templates/custom_template.pptx \
  --output .pptx/extract/custom
```

#### Step 3: JSON 仕様更新

```json
{
  "slides": [
    {
      "id": "slide_new",
      "layout": "Custom Layout Name",
      "title": "カスタムスライド",
      "bullets": [...]
    }
  ]
}
```

### 12.2 カスタム AI ポリシー

#### Step 1: ポリシーファイル作成

```json
// config/custom_prepare_policy.json
{
  "policy_id": "custom_v1",
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000,
  "prompt_template": "カスタムプロンプト:\n{content}\n\n指示: ..."
}
```

#### Step 2: ポリシー ID を環境変数で指定

```bash
export PREPARE_POLICY_ID=custom_v1
uv run pptx prepare samples/input/pitch.md --mode dynamic
```

### 12.3 カスタムバリデーションルール

#### Step 1: pipeline_rules.json 編集

```json
{
  "forbidden_words": [
    "カスタム禁止ワード1",
    "カスタム禁止ワード2"
  ],
  "analyzer": {
    "min_font_size": 12,  // 既定値を上書き
    "margin_in": 0.75
  }
}
```

#### Step 2: カスタムルールを指定

```bash
uv run pptx gen .pptx/compose/generate_ready.json \
  --rules config/custom_rules.json
```

### 12.4 外部ツール連携

#### Office.js アドイン（将来拡張）

```typescript
// src/office-addin/taskpane.tsx
import { generatePPTX } from './api';

async function onGenerate() {
  const spec = await loadSpec();
  const result = await generatePPTX(spec);
  // PowerPoint に挿入
}
```

#### REST API（将来拡張）

```python
# src/pptx_generator/api/app.py
@app.post("/generate")
async def generate_pptx(spec: GenerateRequest):
    # Stage 1-4 を実行
    return {"pptx_url": "...", "pdf_url": "..."}
```

---

## 第13章: 制約事項・既知の問題

### 13.1 技術的制約

| 項目 | 制約内容 |
|------|---------|
| テンプレート形式 | .pptx のみ対応（.potx は未対応） |
| 画像生成 | 外部画像取得・生成は未対応（ロゴのみ） |
| アニメーション | 未対応 |
| SmartArt | 未対応（代替として表・グラフを推奨） |
| 動画埋め込み | 未対応 |
| 数式 | 未対応 |
| 複雑な図形 | 一部制限あり（グループ化図形など） |

### 13.2 既知の問題

#### Issue 1: LibreOffice 変換の文字化け

**症状**: 日本語フォントが LibreOffice に含まれていない場合、PDF で文字化け

**回避策**:
- システムに日本語フォントをインストール
- テンプレートで埋め込みフォントを利用

#### Issue 2: Polisher の段落スタイル上書き

**症状**: 一部のレイアウトで段落スタイルが意図せず変更される

**回避策**:
- `--no-polisher` で Polisher を無効化
- `config/polisher-rules.json` で対象ルールを調整

#### Issue 3: レイアウト適合度スコアの誤判定

**症状**: 適切なレイアウトが選ばれない場合がある

**回避策**:
- `config/layout_ai_policies.json` でスコアリングルールを調整
- `--show-layout-reasons` でスコア内訳を確認

### 13.3 将来的な改善予定

**ロードマップ参照**: `docs/roadmap/roadmap.md`

**主要な拡張機能**:
- Office.js アドインによるワンクリック整形
- LLM レビューコメント生成
- 既存 PPTX からの JSON 逆生成
- 多言語対応（英語・中国語）
- Keynote/Google Slides 互換出力

---

## 第14章: ベストプラクティス

### 14.1 テンプレート設計

#### DO

✅ レイアウトごとに明確な用途を定義する
✅ アンカー名は一貫した命名規則を使う
✅ プレースホルダーを優先的に利用する
✅ ブランドカラー・フォントをテーマ設定で管理する
✅ サンプルスライドは本番前に削除する

#### DON'T

❌ 同一レイアウト内で重複するアンカー名を使わない
❌ アンカー無しでピクセル単位の座標を指定しない
❌ 複雑すぎるレイアウト（要素が 10 個以上）を作らない
❌ グループ化図形をアンカーとして利用しない

### 14.2 コンテンツ準備

#### DO

✅ Markdown で章立てを明確にする
✅ 箇条書きは 3 階層以内に収める
✅ タイトルは 25 文字以内を目安にする
✅ 本文は 1 行 40 文字以内を目安にする

#### DON'T

❌ 禁則語を含めない（`src/pptx_generator/config/pipeline_rules.json` で定義）
❌ 極端に長い段落（200 文字超）を避ける
❌ 文字装飾（太字・斜体）を多用しない

### 14.3 パイプライン実行

#### DO

✅ Stage 1 の抽出結果を必ず確認する
✅ Stage 2 の AI ログで警告をチェックする
✅ Stage 3 のフォールバックレポートを確認する
✅ Stage 4 の analysis.json でエラーをチェックする
✅ 本番実行前に `--debug` でドライラン

#### DON'T

❌ エラーを無視して次の Stage に進まない
❌ テンプレート変更後に抽出をスキップしない
❌ PDF 変換失敗を放置しない

### 14.4 運用管理

#### DO

✅ テンプレート更新時は Golden Sample テストを実行
✅ 監査ログを定期的にアーカイブ
✅ 脆弱性スキャンを週次で実行
✅ CI/CD パイプラインでテストを自動化

#### DON'T

❌ 本番テンプレートを直接編集しない（バージョン管理）
❌ API キーをコードにハードコードしない
❌ .pptx 以外の形式（.potx）を使用しない

---

## 付録A: 用語集

| 用語 | 説明 |
|------|------|
| Stage | パイプラインの主要フェーズ（1: テンプレート、2: 準備、3: マッピング、4: レンダリング） |
| PrepareCard | Stage 2 で生成される構造化コンテンツの単位 |
| jobspec | テンプレート依存の仕様カタログ（Stage 1 出力） |
| generate_ready | レイアウト割り当て済みの描画仕様（Stage 3 出力） |
| Anchor | テンプレート図形名。JSON から特定位置を参照するための識別子 |
| Layout | スライドレイアウト。テンプレートで定義された雛形 |
| Placeholder | PowerPoint のプレースホルダー。タイトル・本文などの既定領域 |
| HITL | Human-in-the-Loop。人間による承認・差戻しを含むフロー |
| Template AI | レイアウトの usage_tags を推定する LLM サービス（Stage 1） |
| Prepare AI | 資料データから PrepareCard を生成する LLM サービス（Stage 2） |
| Layout AI | カードとレイアウトの適合度をスコアリングする LLM サービス（Stage 3） |
| Analyzer | PPTX の品質診断を行うコンポーネント（Stage 4） |
| Refiner | 自動補正を行うコンポーネント（Stage 4） |
| Polisher | Open XML SDK による仕上げ処理（Stage 4） |
| Golden Sample | テンプレート検証用の既知 JSON 仕様 |
| usage_tags | レイアウトの用途を表すタグ（intent + media） |
| story_phase | スライドの章フェーズ（opening/body/closing） |
| Blueprint | Static モード用のテンプレート構造定義 |
| Slot | Blueprint 内のコンテンツ差し込み枠 |

---

## 付録B: 関連ドキュメント索引

### プロジェクト管理

- `README.md`: プロジェクト概要・クイックスタート
- `CONTRIBUTING.md`: 開発ルール・ブランチ戦略
- `CLAUDE.md`: コーディングエージェント向けガイド

### 要件・設計

- `docs/requirements/requirements.md`: 機能要件・非機能要件
- `docs/design/design.md`: システム設計・コンポーネント構成
- `docs/design/cli/cli-command-reference.md`: CLI コマンドリファレンス
- `docs/design/stages/`: Stage 別設計ドキュメント

### ポリシー

- `docs/policies/policies.md`: ポリシードキュメント索引
- `docs/policies/config-and-templates.md`: 設定・テンプレート管理
- `docs/policies/task-management.md`: タスク管理プロセス
- `docs/policies/context-engineering.md`: ドキュメント階層とコンテキスト設計

### 運用

- `docs/runbooks/runbooks.md`: 運用手順書索引
- `docs/runbooks/release.md`: リリース手順
- `docs/runbooks/support.md`: サポート・問い合わせ対応

### 開発

- `tests/AGENTS.md`: テスト戦略・ケース設計
- `src/AGENTS.md`: 実装ガイド
- `scripts/AGENTS.md`: スクリプト運用

### ロードマップ

- `docs/roadmap/roadmap.md`: 機能ロードマップ・進捗管理
- `docs/todo/`: タスク ToDo ファイル

---

## 付録C: サンプルコード

### Python API 利用例

```python
from pptx_generator.pipeline.renderer import Renderer
from pptx_generator.spec_loader import load_spec

# JSON 仕様を読み込み
spec = load_spec("samples/json/sample_spec.json")

# テンプレートを指定してレンダリング
renderer = Renderer(template_path="samples/templates/templates.pptx")
prs = renderer.render(spec)

# PPTX を保存
prs.save("output/proposal.pptx")
```

### CLI スクリプト例

```bash
#!/bin/bash
# フルパイプライン実行スクリプト

set -e  # エラー時に停止

# 変数設定
TEMPLATE="samples/templates/templates.pptx"
CONTENT="samples/input/pitch.md"
OUTPUT_BASE=".pptx"

# Stage 1: テンプレート抽出
echo "Stage 1: テンプレート抽出"
uv run pptx template "$TEMPLATE" --output "$OUTPUT_BASE/extract"

# Stage 2: コンテンツ準備
echo "Stage 2: コンテンツ準備"
uv run pptx prepare "$CONTENT" \
  --mode dynamic \
  --output "$OUTPUT_BASE/prepare"

# Stage 3: マッピング
echo "Stage 3: マッピング"
uv run pptx compose "$OUTPUT_BASE/extract/jobspec.json" \
  --prepare-cards "$OUTPUT_BASE/prepare/prepare_card.json" \

# Stage 4: レンダリング + PDF 生成
echo "Stage 4: レンダリング"
uv run pptx gen "$OUTPUT_BASE/compose/generate_ready.json" \
  --output "$OUTPUT_BASE/gen" \
  --export-pdf

echo "完了: $OUTPUT_BASE/gen/proposal.pptx"
echo "PDF: $OUTPUT_BASE/gen/proposal.pdf"
```

---

## 付録D: FAQ

### Q1: テンプレートは PowerPoint 以外で作成できますか？

A: いいえ。現在は PowerPoint で作成した .pptx ファイルのみ対応しています。Keynote や Google Slides で作成したファイルは、PowerPoint で開いて .pptx として保存し直してください。

### Q2: 生成した PPTX を PowerPoint で開くと崩れることはありますか？

A: python-pptx は Office Open XML 仕様に準拠していますが、一部の高度な機能（アニメーション、SmartArt など）は未対応です。テンプレート設計時にこれらの機能を避けることを推奨します。

### Q3: LLM API を使わずに動作させることはできますか？

A: はい。`PPTX_LLM_PROVIDER=mock` を設定すると、静的ルールベースで動作します。ただし、AI による最適化は利用できません。

### Q4: 大量の提案書を一度に生成できますか？

A: CLI を並列実行することで可能です。将来的には Azure Functions / AWS Lambda での分散実行もサポート予定です。

### Q5: 既存の PPTX から JSON 仕様を逆生成できますか？

A: 現在は未対応ですが、将来拡張として検討中です（`docs/roadmap/roadmap.md` 参照）。

### Q6: カスタムフォントを使用できますか？

A: テンプレートで指定したフォントが使用されます。システムにインストールされていないフォントは代替フォントで描画される場合があります。

### Q7: PDF 変換が失敗する場合の対処法は？

A:
1. LibreOffice がインストールされているか確認
2. `--libreoffice-path` でパスを明示指定
3. `--pdf-timeout` でタイムアウトを延長
4. それでも失敗する場合は `--no-polisher` を試す

### Q8: テンプレート更新時の影響範囲を確認するには？

A: `--baseline-release` オプションで過去のリリースメタと比較し、差分レポート (`diff_report.json`) を確認してください。

---

## 付録E: バージョン履歴

| バージョン | リリース日 | 主な変更点 |
|-----------|-----------|-----------|
| 0.1.0 | 2024-12-01 | 初回リリース（Stage 1-4 基本実装） |
| 0.2.0 | 2024-12-15 | Template AI 連携追加 |
| 0.3.0 | 2025-01-10 | Static Mode 対応 |
| 0.4.0 | 2025-01-20 | HITL 承認フロー実装 |
| 0.5.0 | （予定） | Office.js アドイン対応 |

---

**ドキュメント情報**

- **作成日**: 2025-12-03
- **バージョン**: 1.0
- **対象システムバージョン**: pptx_generator 0.4.0+
- **最終更新日**: 2025-12-03

---

本ドキュメントは PPTX Generator プロジェクトの技術仕様を網羅的にまとめたものです。最新情報は GitHub リポジトリの `docs/` ディレクトリを参照してください。
