# pptx_generator 設計ドキュメント

## このドキュメントの読み方
- 全体構成を把握したい場合は「1. システム全体像」と「2. コンポーネント構成」を先に確認してください。
- 工程ごとの振る舞いは「3. データフロー」と付属のステージ別設計ドキュメントを参照します。
- JSON スキーマやバリデーションルールなど詳細仕様は必要に応じて後半の章（4〜7 章）を確認する構成にしています。

## 既存AIサービス比較・本プロジェクト選定理由

- 代表的なAI PowerPoint自動生成サービス（Copilot, Canva, Gamma, Autoppt, SlidesAI, Presentations.ai等）は、デザインや構成支援に強みがある一方、社内ブランド・日本語対応・細かなレイアウト調整・禁則処理などに制約がある。
- 本プロジェクトは「社内向け提案書を自動生成し、ブランド・レイアウト・日本語品質を担保する」ことを目的とし、python-pptx＋Open XML SDKによる柔軟な制御・カスタマイズ性を重視している。
- 既存サービスの限界（アニメーション・SmartArt・禁則・日本語フォント・PPTX出力の品質）を補うため、独自パイプライン設計・テンプレート運用・自動診断/補正機能を実装する。

## 1. システム全体像
- インプット: 案件情報を整理した JSON 仕様、添付データ（画像、表データ）。
- パイプライン: アウトライン生成 → バリデーション → レンダリング → 自動診断・補正 → 仕上げ → 出力・配信。
- アウトプット: PPTX（必須）、PDF（任意）、解析レポート、監査ログ。
- 実行形態: CLI、REST API、キュー駆動バッチをサポート。

## 2. コンポーネント構成
| コンポーネント | 役割 | 主な技術 |
| --- | --- | --- |
| Service-A Outliner | LLM による章立て生成、JSON 化 | Python, OpenAI API 等 |
| Service-B Validator | 禁則・表記・数値の検証、修正候補提示 | Python, `pydantic` |
| Service-C Renderer | `python-pptx` を用いた PPTX 生成 | Python, `python-pptx`, `Pillow` |
| Service-D Analyzer | PPTX 解析、幾何・タイポ情報抽出 | Python, `python-pptx`, Open XML 解析 |
| Service-D Refiner | `analysis.json` に基づく自動補正 | Python |
| Service-E Polisher | Open XML SDK による最終調整 | .NET 8, Open XML SDK |
| Service-F PDF Exporter | LibreOffice を用いた PPTX→PDF 変換と再試行制御 | Python, LibreOffice CLI |
| Service-G Distributor | ストレージ保存、通知、ログ登録 | Python, Azure SDK / AWS SDK |

## 3. データフロー
最新ロードマップでは、以下の 6 工程で資料を生成する。詳細な検討内容は `docs/notes/20251011-roadmap-refresh.md` を参照。

README の「アーキテクチャ概要」節にも同じ 6 工程を視覚化した Mermaid フローを掲載しているため、工程の全体像を素早く把握したい場合は併せて確認する。

1. **テンプレ準備**（自動）  
   テンプレ資産（`.pptx`）を整備し、バージョン管理を行う。差分検証は工程 2 で実施。
2. **テンプレ構造抽出**（自動）  
   テンプレからレイアウト情報を抽出し、`layouts.jsonl` / `diagnostics.json` を生成。収容目安はヒントとして扱う。
3. **ブリーフ正規化**（HITL）  
   ブリーフ入力を BriefCard に整形し、AI 補助と監査ログを付与した `brief_cards.json` を確定する。承認フローやログ仕様は `docs/requirements/stages/stage-03-content-normalization.md` を参照。
4. **ドラフト構成設計**（HITL）  
   章立て・ページ順・`layout_hint` を決定し、`draft_approved.json` を確定。構成操作は Draft API / CLI を通じて実行し、承認ゲートは Approval-First Policy (`docs/policies/task-management.md`) と連携する。
5. **マッピング**（自動）  
   テンプレ構造（工程 2）と Brief / ドラフト成果物（工程 3/4）を突合し、レイアウト選定とプレースホルダ割付を行う。結果は `rendering_ready.json` と `mapping_log.json` に記録。
6. **PPTX レンダリング**（自動）  
   `rendering_ready.json` とテンプレを用いて `output.pptx` を生成し、軽量整合チェックと `rendering_log.json` を出力。PDF 変換、Polisher、Distributor などの後工程は従来どおり。

工程 3・4 は Human-in-the-Loop (HITL) を前提とし、部分承認・差戻し・Auto-fix 提案をサポートする。AI レビュー仕様と状態遷移は後述および `docs/design/schema/stage-03-content-normalization.md` にまとめている。

### 3.1 状態遷移と中間ファイル
| ステージ | 入力 | 出力 | 備考 |
| --- | --- | --- | --- |
| ブリーフ正規化 | ブリーフ入力（Markdown / JSON） | `brief_cards.json`, `brief_log.json`, `ai_generation_meta.json` | BriefCard 生成、監査ログ（`audit_log.json`） |
| ドラフト構成 | `brief_cards.json`, `layouts.jsonl` | `draft_draft.json` → `draft_approved.json` | 章レーン構成データ（CLI / API 提供）、付録への退避、承認ログ（`draft_review_log.json`） |
| マッピング | `draft_approved.json`, `brief_cards.json`, `layouts.jsonl` | `rendering_ready.json`, `mapping_log.json` | ルールベース＋AI 補完、フォールバック（縮約→分割→付録） |
| レンダリング | `rendering_ready.json`, `template.pptx` | `output.pptx`, `rendering_log.json`, `audit_log.json` | 軽量整合チェック（空 PH / 表 / layout ミスマッチ） |

各 JSON のスキーマは `docs/design/schema/README.md` 配下に記載し、実装は `pptx_generator/models.py`・テストは `tests/` 配下で検証する。

### 3.2 工程別設計ドキュメント
| 工程 | 設計ドキュメント | 主な設計観点 |
| --- | --- | --- |
| 1 テンプレ準備 | [stage-01-template-preparation.md](./stages/stage-01-template-preparation.md) | Release CLI、差分診断、ゴールデンサンプル運用 |
| 2 テンプレ構造抽出 | [stage-02-template-structure-extraction.md](./stages/stage-02-template-structure-extraction.md) | 抽出パイプライン、スキーマ検証、差分レポート |
| 3 コンテンツ正規化 | [stage-03-content-normalization.md](./stages/stage-03-content-normalization.md) | 承認 API（UI はバックログ）、AI レビュー、監査ログ |
| 4 ドラフト構成設計 | [stage-04-draft-structuring.md](./stages/stage-04-draft-structuring.md) | layout_hint 管理 API、スコアリング、章承認ログ |
| 5 マッピング | [stage-05-mapping.md](./stages/stage-05-mapping.md) | スコアリング、フォールバック制御、AI 補完 |
| 6 PPTX 生成 | [stage-06-rendering.md](./stages/stage-06-rendering.md) | レンダリング制御、整合チェック、PDF/Polisher 連携 |

### 3.3 工程別入出力一覧
| ファイル名 | 必須区分 | 概要 | 使用する工程 |
|-------------|-----------|------|---------------|
| template.pptx | 必須（ユーザー準備） | ユーザー準備のPPTXテンプレ。以後の全工程で参照されるベース。 | S1 入 / S1 出 / S2 入 / S5 入 / S6 入 |
| template_release.json | 任意 | テンプレのリリースメタ。差分・版管理用。 | S1 入（過去版） / S1 出 |
| release_report.json | 任意 | テンプレ差分レポート。 | S1 出 |
| golden_runs/* | 任意 | ゴールデンテスト実行結果。テンプレ検証用。 | S1 出 |
| branding.json | 準必須 | テンプレから抽出したブランド設定。スタイル適用に使用。 | S2 出 / S5 入 / S6 入 |
| layouts.jsonl | 任意（推奨） | テンプレのレイアウト構造。ヒント/検証に使用。 | S2 出 / S4 入 / S5 入 |
| diagnostics.json | 任意 | 抽出/検証時の診断。 | S2 出 |
| diff_report.json | 任意 | 抽出結果の差分レポート。 | S2 出 |
| brief_source.(md/json) | 必須（ユーザー準備） | ブリーフ入力。章カード生成の元データ。 | S3 入 |
| brief_cards.json | 必須 | ブリーフ正規化の成果物。以後の中核データ。 | S3 出 / S4 入 / S5 入 |
| brief_log.json | 任意 | ブリーフレビューのログ。トレーサビリティ。 | S3 出 / S4 入 / S5 入 |
| ai_generation_meta.json | 任意 | ブリーフ生成の統計・入力ハッシュ。 | S3 出 / S4 入 |
| brief_story_outline.json | 任意 | 章構造とカード紐付け。 | S3 出 / S4 入 |
| draft_approved.json | 必須 | 人手承認済みドラフト。ページ順/章立て確定。 | S4 出 / S5 入 |
| draft_meta.json | 任意 | ドラフト工程のメタ情報。 | S4 出 |
| draft_review_log.json | 任意 | ドラフトレビューのログ。 | S4 出 / S5 入 |
| rules.json | 任意 | 文字量や禁止語などの規則。マッピング/解析に使用。 | S5 入 / S6 入 |
| rendering_ready.json | 必須 | マッピング結果。レイアウト割付済みの描画直前仕様。 | S5 出 / S6 入 |
| mapping_log.json | 任意 | マッピング過程のログ。レイアウトスコア等。 | S5 出 |
| fallback_report.json | 任意 | フォールバック発生の記録。 | S5 出 |
| proposal.pptx | 必須（最終成果物） | **最終成果物** PPTX。 | S6 出 |
| proposal.pdf | 任意（最終成果物） | **最終成果物** PDF。指定時のみ生成。 | S6 出 |
| analysis.json | 任意 | 生成物の詳細解析結果。 | S6 出 |
| rendering_log.json | 任意 | レンダリングの要約ログ。 | S6 出 |
| audit_log.json | 任意 | 実行監査ログ。 | S6 出 |
| review_engine_analyzer.json | 任意 | レビュー用に整形した解析出力。 | S6 出 |
| analysis_snapshot.json | 任意 | 構造スナップショット。PH対応の記録。 | S6 出 |
| polisher + rules | 任意 | 仕上げ調整用。Polisher利用時に使用。 | S6 入 |
| PDF出力設定 | 任意 | LibreOffice等のPDF変換設定。 | S6 入 |

### 3.3 レイアウトカバレッジ指針 (RM-043)
- テンプレ標準 `samples/templates/templates.pptx` は 50 ページ規模のカバレッジを確保し、セクション区切り・ビジネスサマリー・タイムライン・KPI・財務・組織・プロセス・リスク・データビジュアル・クロージングの各カテゴリへ最低 3 パターンずつ割り当てる。
- アンカー名はカード／チャート／CTA など用途が判別できる語を用い、`BrandLogo`・`Section Title` のように共通要素は既存レイアウトと整合させる。動的要素（フロー矢印など）がプレースホルダーでない場合は JSON で参照しない。
- 抽出結果は `uv run pptx layout-validate --template samples/templates/templates.pptx --output .pptx/validation/rm043` で取得し、`samples/json/sample_template_layouts.jsonl` と `samples/json/sample_jobspec.json` に反映してマッピングテストの基準データとする。
- 追加テンプレを受領した際は `analysis_snapshot.json` を比較し、レイアウト名・アンカー名の不一致を ToDo へ記録して修正フローを回す。

## 4. JSON スキーマ詳細
詳細な更新履歴やフィールド説明は `docs/design/schema/README.md` を参照してください。ここでは代表的な項目構成を抜粋します。
```yaml
meta:
  schema_version: string
  title: string
  client: string
  author: string
  created_at: date
  theme: string
  locale: string
auth:
  created_by: string
  department: string
slides:
  - id: string
    layout: string
    title: string
    subtitle: string
    notes: string
    bullets:
      - id: string
        text: string
        level: int
        font:
          size_pt: int
          bold: bool
          italic: bool
          color_hex: string
    tables:
      - id: string
        anchor: string
        columns: [string]
        rows: [[string|number]]
        style:
          header_fill: string
          zebra: bool
    charts:
      - id: string
        anchor: string
        type: string
        categories: [string]
        series:
          - name: string
            values: [number]
            color_hex: string
        options:
          data_labels: bool
          y_axis_format: string
    images:
      - id: string
        anchor: string
        source: string
        sizing: string
        position:
          left_in: float
          top_in: float
          width_in: float
          height_in: float
    textboxes:
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
          align: string
          left_indent_in: float
          right_indent_in: float
          first_line_indent_in: float
- レンダラーはアンカー指定されたテキストボックスを挿入する際、テンプレート側の図形名を新しいテキストボックスへ引き継ぎ、後続工程が同名アンカーで参照できるようにする。
- 段落スタイルは `config/branding.json` の `components.textbox.paragraph` またはレイアウト別 `layouts.*.placements.*.paragraph` から取得し、Renderer が段落揃え・行間・余白・インデント（左／右／一行目）を描画時に適用する。個別スライドで `paragraph` パラメータを指定した場合はブランド既定を上書きする。
assets:
  fonts: [{ name: string, url: string }]
  images: [{ id: string, url: string }]
```
- `anchor` を指定した場合はテンプレート上の図形／プレースホルダーを基準に描画し、未指定時は `position` の座標を使用する。
- フォーマット検証は `pydantic` で実装し、必須項目不足・型不一致を例外化。

## 5. バリデーションルール
- **禁則語**: `config/rules.json` のリストにマッチ。
- **表記揺れ**: 正式名称マッピング辞書で置換。
- **数値整合性**: 指標ごとの範囲定義、金額桁数チェック。
- **文字数**: タイトル <= 25 文字、本文行 <= 40 文字、行数 <= 6。
- **画像解像度**: 表示幅に対し 150dpi 未満で警告。
- **リンク検証**: 設定で切り替え可能な HEAD リクエスト。

## 6. テンプレート設計
- `templates/layout_map.yaml` でレイアウト名・プレースホルダ ID・座標・サイズを管理。
- ブランドカラー・フォントおよびレイアウト別スタイルを `config/branding.json` (`theme` / `components` / `layouts`) に定義し、Renderer・Analyzer・Polisher が共有。
- 共通フッター: 文言、日付プレースホルダ、ページ番号、ロゴの固定配置。
- 更新フロー: テンプレート改訂時に差分を `docs/adr/` に記録、`TemplateVersion` をインクリメント
- テンプレートファイルは .pptx 形式のみ対応。.potxを利用する場合は、PowerPointで新規 .pptx を作成して保存してください。

## 7. 自動診断・補正ロジック
- Analyzer: PPTX の DrawingML を解析し、図形位置 (EMU)、サイズ、フォント情報を抽出。
  - レンダラーで付与したアンカー名／図形 ID を基に箇条書き・テキストボックス・画像を突合し、実体から得たメトリクスを `analysis.json` へ記録する。
  - スライド余白 (10.0in × 7.5in) とグリッド 0.125in を基準に `margin` と `grid_misaligned` を判定し、移動提案を `fix.payload` に含める。
- Issue タイプ:
  - `margin`: スライド余白からの逸脱。
  - `grid_misaligned`: グリッド 0.125in からのズレ。
  - `font_min`: フォントサイズが規定未満。
  - `contrast_low`: 背景と文字色のコントラスト不足 (WCAG 2.1 AA)。
  - `bullet_depth`: 箇条書きレベルが上限超え。
  - `layout_consistency`: 箇条書きのインデントジャンプ。
- Fix タイプ:
  - `move`: 指定デルタで位置調整。
  - `font_raise`: 最小フォントサイズまで引き上げ。
  - `color_adjust`: テーマカラーへの置換。
  - `bullet_cap`: 箇条書きレベルの切り上げ。
  - `bullet_reindent`: 許容範囲へレベルを再設定。
- Refiner: `bullet_reindent` を起点に JSON テンプレ段階で段階的な補正を行い、調整結果をアーティファクトとして記録する。
- コントラスト判定は通常 4.5:1 を採用しつつ、フォントサイズが `large_text_threshold_pt` 以上の場合は 3.0:1 を閾値として扱い、メトリクスに `required_ratio` と `font_size_pt` を記録する。

## 8. 仕上げ処理 (Open XML SDK)
- `.NET` プロジェクト `dotnet/OpenXmlPolish` を配置。
- `rules/polish.yaml` でフォント最小値や色の統一、段落間隔（必要時のみ）を定義。段落インデント／行間などブランド既定のスタイルは Renderer 側で適用し、Polisher はフォールバック修正と監査ログ出力に専念する。
- 処理手順:
  1. `PresentationDocument.Open` で PPTX をロード。
  2. 指定スライドを走査し、必要最小限の ParagraphProperties（フォントサイズ・色など）を更新。
  3. テーマ色にリンクされていない RGB を Accent カラーへマップ。
  4. 最低フォントサイズを再確認し、以下の Run を調整。
  5. 保存後に差分ログを出力。

## 9. 技術スタック
- 言語: Python 3.11, TypeScript (将来的な Office.js), C# (.NET 8)。
- フレームワーク: FastAPI (REST), Azure Functions / AWS Lambda (サーバーレス)、Docker。
- ライブラリ: `python-pptx`, `Pillow`, `pydantic`, `ruff`, `mypy`, Open XML SDK, LibreOffice。
- インフラ: Azure Storage (Blob/Queue), Key Vault, App Insights, Azure Container Apps（候補）。

## 10. 運用・監視
- ログ: `JobId`, 入力ハッシュ, 処理時間, issues 件数, エラー詳細を構造化ログ (JSON) で出力。
- メトリクス: 生成時間、LibreOffice 変換時間、エラー率、再試行回数。
- アラート: `critical` issue 発生、変換失敗連続、テンプレート検証エラー、外部 API 障害。
- Runbook: 正常系・異常系の手順を docs/runbook.md で管理。
- 監査: CLI が `outputs/audit_log.json` を生成し、`pdf_export_metadata` をメトリクス基盤に取り込むことで LibreOffice 成功率とリードタイムを可視化する。
- 監査ログには `refiner_adjustments` を含め、適用済みの自動補正履歴を追跡可能とする。

## 11. セキュリティ設計
- データ暗号化: ストレージに保存するファイルを SSE (Storage-side Encryption) + 任意でクライアント暗号化。
- API 認証: Azure AD / OAuth2 を想定。CLI は PAT or SAS トークン。
- LLM 通信: プロンプトとレスポンスを監査ログに記録、機密情報はプレースホルダ化。
- 脆弱性管理: 週次 Dependabot / Renovate、`pip-audit` と `dotnet list package --vulnerable` を CI で実行。

## 12. リスクと対策
| リスク | 影響 | 対策 |
| --- | --- | --- |
| テンプレ更新によるレイアウト崩れ | 生成失敗・不正配置 | `template_validator.py` で自動検証、CI に組み込み |
| LLM 出力の構造崩れ | パース失敗 | JSON スキーマで厳密検証、必要箇所はテンプレートプロンプト固定 |
| LibreOffice 変換失敗 | PDF 未生成 | 3 回リトライ、代替 API (Graph) のフェイルオーバー |
| ブランド変更の遅延反映 | 品質低下 | `branding.json` を参照する構成、PR ワークフローで早期反映 |
| セキュリティ事故 | 情報漏えい | RBAC, ログ監査, API Key 管理, 匿名化プロセス |

## 13. 将来拡張
- Office.js アドイン (`manifest.xml`, React UI, Graph API) によるワンクリック整形ボタン。
- LLM によるレビューコメント生成パイプライン（analysis.json + スライド PNG を入力）。
- 既存 PPTX から JSON 仕様を生成する `reverse_engineer.py`。
- 多言語対応のためのフォントセット定義とテンプレ差し替え機能。
- Keynote/Google Slides 互換出力用の変換モジュール。

## 14. ファイル配置案
```
project/
 ├─ python/
 │   ├─ renderer.py
 │   ├─ analyze.py
 │   ├─ refine.py
 │   ├─ config/
 │   │   ├─ branding.json
 │   │   └─ rules.json
 │   └─ tests/
 ├─ dotnet/
 │   └─ OpenXmlPolish/
 │       ├─ Program.cs
 │       └─ rules/polish.yaml
 ├─ templates/
 │   ├─ corporate_default_v1.pptx
 │   └─ layout_map.yaml
 ├─ docs/
 │   ├─ requirements/
 │   │   └─ overview.md
 │   ├─ design/
 │   │   └─ overview.md
 │   └─ policies/
 │       └─ task-management.md
 ├─ scripts/
 │   ├─ run_pipeline.sh
 │   └─ run_pipeline.ps1
 └─ .github/
     ├─ workflows/
     └─ dependabot.yml
```
