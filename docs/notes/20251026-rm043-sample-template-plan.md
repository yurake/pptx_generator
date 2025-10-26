# 2025-10-26 RM-043 サンプルテンプレ拡充 初期整理

## 1. 現行サンプルの棚卸し

- `samples/json/sample_spec.json`
  - 12 ページ構成 / 7 レイアウト種別。
  - `Two Column Detail` が 5 枚と偏りが大きく、タイムライン・比較・ファクトシート以外の特殊レイアウトが不足。
  - 表／画像／テキストボックスの組み合わせも限定的（グラフ未使用）。
- `samples/json/sample_spec_minimal.json`
  - `Title`＋`One Column Detail` の 2 枚のみ。
- `samples/json/sample_content_approved.json`
  - 3 カード（cover / agenda / problem）のみで intent/type が限定的。
- `samples/json/sample_layouts.jsonl`
  - 2 レコード（overview/detail）しかなく、用途タグやヒントの検証に十分でない。

## 2. 追加レイアウト案（50 ページ目標）

| カテゴリ | 想定枚数 | 主な要素 / 要件 |
| --- | --- | --- |
| セクション / 区切り | 4 | シンプルカバー、写真強調、章タイトル＋注釈、シンボルアイコン。 |
| ビジネスサマリー | 5 | 3 カラムまとめ、アイコン付 KPI、ベネフィットカード、バリュープロポジション、1 ページサマリー。 |
| 課題 / 機会 | 3 | 箇条書き＋強調ボックス、Before/After、Pain/Gain テーブル。 |
| ソリューション / 施策 | 5 | サービス構成図、モジュール一覧、段階的ソリューション、フェーズ別効果、プログラム全体像。 |
| タイムライン / ロードマップ | 5 | 月次ロードマップ、四半期ガント、里程票＋取り組み、縦型スケジュール、マイルストーン＋担当。 |
| KPI / メトリクス | 5 | KPI ボード、ゲージ＋数値、フォーカス指標、OKR マップ、ハイライトカード。 |
| 財務 / リソース | 4 | 予算テーブル、コスト構成、リソース配分ヒートマップ、ROI 試算。 |
| 組織 / 体制 | 4 | 体制図、RACI ボード、担当者一覧、サポート窓口。 |
| プロセス / ワークフロー | 5 | ステップ図、循環プロセス、泳線図簡易版、チェックリスト、実行ロードマップ。 |
| リスク / FAQ | 3 | リスクテーブル、課題と対策、FAQ 形式。 |
| データ / チャート | 4 | 折れ線・棒・ドーナツ・ヒートマップ。 |
| クロージング / CTA | 3 | 次アクション＋CTA、まとめ＋連絡先、感謝＋問い合わせ。 |

→ 合計 50 ページ（既存 12 ページを除き +38 ページ分のテンプレ候補）。

### アンカー／要素要件のメモ
- グラフ系レイアウトに `Chart Placeholder` を追加し、`chart_*` アンカーを実装。
- カード系は画像・アイコン併用前提で `Icon`, `Illustration` アンカーを命名。
- 体制・RACI はテーブル＋メモ用テキストボックス、パス名 `RoleMatrix`, `ResponsibilityNotes` など。
- 区切り・CTA はブランドロゴ／背景画像の差し替え対応のため、画像アンカーを必須化。

## 3. サンプル JSON / アセット拡張方針

- `sample_spec.json` は既存 12 枚を保持しつつ `sample_spec_extended.json` を新設し 50 ページ構成を定義。
- `sample_content_approved.json` / `sample_content_review_log.json` に対応するカード・イベントを追加し、intent/type カバレッジを拡張。
- `sample_layouts.jsonl` を全レイアウト追加後の `layout-validate` 出力を基準に更新し、用途タグ・ヒントを網羅。
- 追加レイアウトに必要なダミー画像・アイコンは `samples/assets/` に SVG/PNG 形式で配置。

## 4. テスト計画（設計段階での確認事項）

- レイアウト検証  
  - `uv run pptx layout-validate --template samples/templates/templates.pptx --output .pptx/validation/rm043`  
  - 生成物: `layouts.jsonl`, `diagnostics.json`, `diff_report.json`。重複アンカー／抽出エラーの有無を確認。
- サンプル生成  
  - `uv run pptx gen samples/json/sample_spec_extended.json --template samples/templates/templates.pptx --output .pptx/gen/rm043 --emit-structure-snapshot`  
  - 生成物: PPTX, `analysis.json`, `analysis_snapshot.json`, `audit_log.json`。全ページの配置とメタ情報を確認。
- CLI テスト  
  - `uv run --extra dev pytest tests/test_cli_integration.py`（必要に応じ `tests/test_renderer.py` など関連テスト）。  
  - 期待値更新に伴う失敗ケースを解消し、追加サンプルが網羅されているかを確認。
- 任意確認  
  - `uv run pptx tpl-extract` で抽出結果を diff し、アンカー命名を表形式で確認。
  - LibreOffice PDF 生成（`uv run pptx gen ... --export-pdf`）をスポット実行し、PDF 出力メタを確認。

## 5. 次アクション

1. 上記カテゴリの詳細要件（アンカー名・必要要素）を PPTX 編集用に整理し、テンプレ作成をユーザーへ依頼。  
2. テンプレ受領後、抽出→JSON 生成→テストを順次実施。  
3. 最終的な成果物と検証結果を ToDo／ロードマップに反映し、レビューへ準備する。

## 6. テンプレ編集指示書（ユーザー向け）

### 6.1 共通ルール
- レイアウト追加先: `samples/templates/templates.pptx`。既存レイアウトを削除せず、新規レイアウトを追加。  
- レイアウト名は英語ベース＋キャメルケース風に統一（例: `SectionCoverSimple`）。  
- アンカー（図形名）は JSON 仕様と同名になるよう設定し、スペースを含めない。  
- テキストプレースホルダーは初期文字列を空に設定。画像・図形は透過塗りまたはダミー画像で配置。  
- 追加レイアウトで利用するアンカー名が既存と重複しても構わないが、同一レイアウト内では一意にする。  
- 画像用アンカーは長方形図形で枠取りし、`Image` 系、`Illustration`、`Icon` など用途に応じた名前を付与。  
- テーブル・チャートは PowerPoint の該当プレースホルダーを配置して命名。  
- 追加レイアウトは 12 種類を基本テンプレとして用意し、同レイアウトの色替えや配置替えで 50 ページ分をカバー予定。

### 6.2 レイアウト定義
| Layout 名 | 想定カテゴリ / 用途 | 必須アンカー | 任意アンカー / 備考 |
| --- | --- | --- | --- |
| `SectionCoverSimple` | セクション区切り（標準） | `SectionTitle`, `SectionSubtitle`, `BrandLogo` | 背景画像を使用する場合は `BackgroundImage` |
| `SectionCoverPhoto` | セクション区切り（写真強調） | `SectionTitle`, `SectionSubtitle`, `HeroImage`, `BrandLogo` | `HeroImage` は全面写真差し替え用 |
| `SummaryThreeColumn` | ビジネスサマリー（3 カラム） | `SummaryLead`, `SummaryColLeft`, `SummaryColCenter`, `SummaryColRight` | アイコン領域が必要なら `SummaryIcons` |
| `SummaryKPIBoard` | KPI 集約 | `KPIHeadline`, `KPIPrimary`, `KPISecondary`, `KPIChart` | `KPIFootnote` |
| `BenefitCards` | ベネフィットカード | `BenefitTitle`, `BenefitCard1`, `BenefitCard2`, `BenefitCard3`, `BenefitIllustration` | カードが 4 枚の場合は `BenefitCard4` を追加 |
| `ProblemBeforeAfter` | 課題 / 解決比較 | `ProblemBefore`, `ProblemAfter`, `ProblemNotes` | 中央アイコン用に `ProblemIcon` |
| `PainGainMatrix` | Pain / Gain テーブル | `PainGainTable`, `PainGainNotes` | |
| `SolutionModules` | ソリューション構成図 | `SolutionTitle`, `SolutionOverview`, `SolutionModules`, `SolutionIllustration` | |
| `PhasedImpact` | フェーズ別効果 | `PhasedTitle`, `PhasedTimeline`, `PhasedBenefits` | |
| `RoadmapQuarterly` | 四半期ロードマップ | `RoadmapTable`, `RoadmapMilestones`, `RoadmapNotes` | |
| `RoadmapVertical` | 縦型ロードマップ | `RoadmapTimeline`, `RoadmapDetails`, `RoadmapNotes` | |
| `KPIHighlight` | KPI ハイライト | `HighlightTitle`, `HighlightPrimary`, `HighlightSecondary`, `HighlightChart` | |
| `FinancialBreakdown` | 財務内訳 | `FinanceTable`, `FinanceNotes`, `FinanceChart` | |
| `ResourceHeatmap` | リソース配分 | `ResourceMatrix`, `ResourceLegend`, `ResourceNotes` | |
| `OrgStructure` | 体制図 | `OrgChart`, `OrgNotes`, `OrgContact` | `OrgPhoto` |
| `RACIOverview` | RACI ボード | `RACIChart`, `RACINotes` | |
| `ProcessSteps` | ステップ図（横並び） | `ProcessHeader`, `ProcessSteps`, `ProcessNotes` | |
| `ProcessLoop` | 循環プロセス | `ProcessLoop`, `ProcessCaption`, `ProcessNotes` | |
| `ChecklistBoard` | チェックリスト | `ChecklistHeader`, `ChecklistItems`, `ChecklistNotes` | |
| `RiskMitigation` | リスクと対策 | `RiskTable`, `RiskNotes` | `RiskIcon` |
| `FAQCards` | FAQ 形式 | `FAQTitle`, `FAQList`, `FAQNotes`, `FAQIllustration` | |
| `DataComboChart` | 複合チャート | `ChartPrimary`, `ChartSecondary`, `ChartNotes` | |
| `DataHeatmap` | データヒートマップ | `Heatmap`, `HeatmapNotes`, `HeatmapLegend` | |
| `ClosingCTA` | クロージング／CTA | `ClosingTitle`, `ClosingBullets`, `ClosingCTA`, `ClosingContact`, `BrandLogo` | |
| `ContactThankYou` | 感謝ページ | `ThankTitle`, `ThankSubtitle`, `ContactInfo`, `ContactQR`, `BrandLogo` | `BackgroundImage` |

> 上表の 24 レイアウトをテンプレートに追加し、構成や色替えで合計 50 ページ分の利用を想定。必要に応じて派生レイアウトをコピーし、アンカー名と配置を調整してもらって構いません。

### 6.3 既存レイアウトとの共存
- 既存の `Title`, `Two Column Detail`, `Timeline Detail` などはそのまま残す。  
- 新レイアウト群はマスター内でグループ化し、分かりやすい順番で並べ替えて構わない。  
- 共通で利用するアンカー（例: `BrandLogo`, `SectionTitle`）は他レイアウトとの整合性を優先。

### 6.4 納品時に必要なもの
- 更新済み `samples/templates/templates.pptx`。  
- 追加レイアウトとアンカー名の一覧（上表との差分があれば注記）。  
- 追加が必要なダミー画像／アイコン（PNG/SVG）をまとめたフォルダ（任意）。  
- 変更メモ（レイアウト追加数、既存レイアウト調整の有無）。

以上の内容で PPTX 編集を実施いただければ、こちらで抽出・サンプル更新・テストを続行できます。
