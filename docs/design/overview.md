# pptx_generator 設計ドキュメント

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
1. `spec.json` を受領し、`JobId` を生成。
2. Validator が JSON スキーマを検証し、`validation_report.json` を出力。問題があれば停止。
3. Refiner が入力 JSON を前処理し、箇条書きレベルの調整など軽微な補正を適用。
4. Renderer がテンプレート（`templates/corporate_default_vN.pptx`）を読み込み、指定レイアウトに沿ってスライドを作成。
5. Analyzer が PPTX から図形位置・テキスト属性を抽出し、`analysis.json` を生成。
6. PDF Exporter が LibreOffice (soffice) により PPTX から PDF を生成し、失敗時はリトライ。
7. Polisher（任意）が Open XML SDK で段落・禁則・色統一を適用し、`proposal_polished.pptx` を作成。
8. Distributor が出力ファイルをストレージへ保存し、メタ情報とともに通知。
9. CLI が `audit_log.json` を生成し、PDF 変換メタデータ（試行回数・所要時間）と Refiner 調整ログを含む監査情報を保存。

## 4. JSON スキーマ詳細
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
- ブランドカラー・フォントを `config/branding.json` に定義し、Renderer・Analyzer・Polisher が共有。
- 共通フッター: 文言、日付プレースホルダ、ページ番号、ロゴの固定配置。
- 更新フロー: テンプレート改訂時に差分を `docs/adr/` に記録、`TemplateVersion` をインクリメント
- テンプレートファイルは .pptx 形式のみ対応。.potxを利用する場合は、PowerPointで新規 .pptx を作成して保存してください。

## 7. 自動診断・補正ロジック
- Analyzer: PPTX の DrawingML を解析し、図形位置 (EMU)、サイズ、フォント情報を抽出。
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
- `rules/polish.yaml` で段落間隔、行間（`SpacingPercent`）、インデント（EMU）、禁則設定 (`EastAsianLineBreak`) を定義。
- 処理手順:
  1. `PresentationDocument.Open` で PPTX をロード。
  2. 指定スライドを走査し、ParagraphProperties を更新。
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
