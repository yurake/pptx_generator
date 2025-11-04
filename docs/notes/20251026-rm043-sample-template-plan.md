# 2025-10-26 RM-043 サンプルテンプレ拡充 初期整理

## 1. 現行サンプルの棚卸し

- `samples/json/sample_jobspec.json`
  - 12 ページ構成 / 7 レイアウト種別。
  - `Two Column Detail` が 5 枚と偏りが大きく、タイムライン・比較・ファクトシート以外の特殊レイアウトが不足。
  - 表／画像／テキストボックスの組み合わせも限定的（グラフ未使用）。
- 旧 `sample_spec_minimal.json` は撤廃し、最小構成のテストは `tests/test_cli_outline.py` で動的生成する。
- `samples/brief/sample_prepare_card.json`（新規追加予定）
  - 3 カード（cover / agenda / problem）のみで intent/type が限定的。
- `samples/json/sample_template_layouts.jsonl`
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

- `sample_jobspec.json` は 50 ページ構成まで拡張し、カテゴリ別レイアウトを網羅する（旧 `sample_spec_extended.json` 案を統合）。
- `sample_prepare_card.json` / `sample_brief_log.json` に対応するカード・イベントを追加し、intent/type カバレッジを拡張。
- `sample_template_layouts.jsonl` を全レイアウト追加後の `layout-validate` 出力を基準に更新し、用途タグ・ヒントを網羅。
- 追加レイアウトに必要なダミー画像・アイコンは `samples/assets/` に SVG/PNG 形式で配置。

## 4. テスト計画（設計段階での確認事項）

- レイアウト検証  
  - `uv run pptx layout-validate --template samples/templates/templates.pptx --output .pptx/validation/rm043`  
  - 生成物: `layouts.jsonl`, `diagnostics.json`, `diff_report.json`。重複アンカー／抽出エラーの有無を確認。
- サンプル生成  
- `uv run pptx gen samples/json/sample_jobspec.json --template samples/templates/templates.pptx --output .pptx/gen/rm043 --emit-structure-snapshot`  
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
| No. | Layout 名 | 想定カテゴリ / 用途 | 必須アンカー | 任意アンカー / 備考 |
| --- | --- | --- | --- | --- |
| 01 | `SectionCoverSimple` | セクション区切り（標準） | `SectionTitle`, `SectionSubtitle`, `BrandLogo` | 背景画像を使用する場合は `BackgroundImage` |
| 02 | `SectionCoverPhoto` | セクション区切り（写真強調） | `SectionTitle`, `SectionSubtitle`, `HeroImage`, `BrandLogo` | `HeroImage` は全面写真差し替え用 |
| 03 | `SectionCoverIconic` | セクション区切り（アイコン強調） | `SectionTitle`, `SectionSubtitle`, `SectionIcon`, `BrandLogo` | `BackgroundTint` |
| 04 | `SummaryExecutiveBoard` | エグゼクティブサマリー | `SummaryLead`, `SummaryBullets`, `SummaryMetrics` | `SummaryNotes` |
| 05 | `SummaryThreeColumn` | ビジネスサマリー（3 カラム） | `SummaryLead`, `SummaryColLeft`, `SummaryColCenter`, `SummaryColRight` | `SummaryIcons` |
| 06 | `SummaryKPIBoard` | KPI 集約 | `KPIHeadline`, `KPIPrimary`, `KPISecondary`, `KPIChart` | `KPIFootnote` |
| 07 | `VisionMissionStatement` | ビジョン／ミッション共有 | `VisionText`, `MissionText`, `MissionIcon` | `MissionNotes` |
| 08 | `BenefitCards` | ベネフィットカード | `BenefitTitle`, `BenefitCard1`, `BenefitCard2`, `BenefitCard3`, `BenefitIllustration` | カード 4 枚時は `BenefitCard4` |
| 09 | `OpportunitySizing` | 市場／機会規模 | `OpportunityHeader`, `OpportunityChart`, `OpportunityNotes` | `OpportunityTable` |
| 10 | `SWOTMatrix` | SWOT | `SWOTStrength`, `SWOTWeakness`, `SWOTOpp`, `SWOTThreat`, `SWOTNotes` | |
| 11 | `QuadrantAnalysis` | 四象限分析 | `QuadrantTL`, `QuadrantTR`, `QuadrantBL`, `QuadrantBR`, `QuadrantAxis` | `QuadrantNotes` |
| 12 | `NineCellMatrix` | 9 象限（3×3）マトリクス | `NineCellGrid`, `NineLegend`, `NineNotes` | |
| 13 | `ProblemBeforeAfter` | 課題／解決比較 | `ProblemBefore`, `ProblemAfter`, `ProblemNotes` | `ProblemIcon` |
| 14 | `PainGainMatrix` | Pain / Gain テーブル | `PainGainTable`, `PainGainNotes` | |
| 15 | `PersonaProfile` | ターゲット像 | `PersonaPhoto`, `PersonaSummary`, `PersonaDetails`, `PersonaNeeds` | |
| 16 | `JourneyMap` | カスタマージャーニー | `JourneyTimeline`, `JourneyPainPoints`, `JourneyNotes` | |
| 17 | `SolutionModules` | ソリューション構成図 | `SolutionTitle`, `SolutionOverview`, `SolutionModules`, `SolutionIllustration` | |
| 18 | `SolutionBlueprint` | ソリューション全体像 | `BlueprintHeader`, `BlueprintDiagram`, `BlueprintNotes` | |
| 19 | `PhasedImpact` | フェーズ別効果 | `PhasedTitle`, `PhasedTimeline`, `PhasedBenefits` | |
| 20 | `ServiceCatalogGrid` | サービスカタログ | `CatalogTitle`, `CatalogGrid`, `CatalogNotes` | |
| 21 | `RoadmapQuarterly` | 四半期ロードマップ | `RoadmapTable`, `RoadmapMilestones`, `RoadmapNotes` | |
| 22 | `RoadmapVertical` | 縦型ロードマップ | `RoadmapTimeline`, `RoadmapDetails`, `RoadmapNotes` | |
| 23 | `RoadmapSwimlane` | 泳線ロードマップ | `RoadmapSwimlanes`, `RoadmapLegend`, `RoadmapNotes` | |
| 24 | `RoadmapJourney` | ストーリーロードマップ | `JourneyMilestones`, `JourneyIcons`, `JourneyNotes` | |
| 25 | `RoadmapGantt` | ガントチャート | `GanttChart`, `GanttLegend`, `GanttNotes` | |
| 26 | `RoadmapCalendar` | カレンダービュー | `CalendarGrid`, `CalendarHighlights`, `CalendarNotes` | |
| 27 | `ImplementationMilestoneWall` | 実行マイルストーン | `MilestoneBoard`, `MilestoneOwners`, `MilestoneNotes` | |
| 28 | `LaunchChecklist` | リリースチェック | `LaunchHeader`, `LaunchChecklist`, `LaunchNotes` | |
| 29 | `KPIHighlight` | KPI ハイライト | `HighlightTitle`, `HighlightPrimary`, `HighlightSecondary`, `HighlightChart` | |
| 30 | `MetricTrendComparison` | 指標比較グラフ | `MetricChart`, `MetricTable`, `MetricNotes` | |
| 31 | `FinancialBreakdown` | 財務内訳 | `FinanceTable`, `FinanceNotes`, `FinanceChart` | |
| 32 | `FinancialScenarioTable` | 財務シナリオ | `ScenarioTable`, `ScenarioChart`, `ScenarioNotes` | |
| 33 | `ResourceHeatmap` | リソース配分 | `ResourceMatrix`, `ResourceLegend`, `ResourceNotes` | |
| 34 | `ResourceAllocationStack` | アロケーション推移 | `ResourceStackChart`, `ResourceSummary`, `ResourceNotes` | |
| 35 | `OrgStructure` | 体制図 | `OrgChart`, `OrgNotes`, `OrgContact` | `OrgPhoto` |
| 36 | `OrgOperatingModel` | 運営モデル | `OperatingDiagram`, `OperatingNotes`, `OperatingOwners` | |
| 37 | `RACIOverview` | RACI ボード | `RACIChart`, `RACINotes` | |
| 38 | `GovernanceTimeline` | ガバナンススケジュール | `GovernanceTimeline`, `GovernanceRoles`, `GovernanceNotes` | |
| 39 | `ProcessSteps` | ステップ図（横並び） | `ProcessHeader`, `ProcessSteps`, `ProcessNotes` | |
| 40 | `ProcessLoop` | 循環プロセス | `ProcessLoop`, `ProcessCaption`, `ProcessNotes` | |
| 41 | `ProcessSwimlane` | 泳線プロセス | `ProcessSwimlane`, `ProcessRoles`, `ProcessNotes` | |
| 42 | `ChecklistBoard` | チェックリスト | `ChecklistHeader`, `ChecklistItems`, `ChecklistNotes` | |
| 43 | `TaskKanban` | タスクボード | `KanbanColumns`, `KanbanNotes`, `KanbanHeader` | |
| 44 | `RiskMitigation` | リスクと対策 | `RiskTable`, `RiskNotes` | `RiskIcon` |
| 45 | `IssueLogBoard` | 課題ログ | `IssueTable`, `IssueOwners`, `IssueNotes` | |
| 46 | `FAQCards` | FAQ 形式 | `FAQTitle`, `FAQList`, `FAQNotes`, `FAQIllustration` | |
| 47 | `SupportContactSheet` | サポート情報 | `SupportChannels`, `SupportNotes`, `SupportIcon` | |
| 48 | `DataComboChart` | 複合チャート | `ChartPrimary`, `ChartSecondary`, `ChartNotes` | |
| 49 | `DataHeatmap` | データヒートマップ | `Heatmap`, `HeatmapNotes`, `HeatmapLegend` | |
| 50 | `DataDashboardSplit` | ダッシュボード分割 | `DashboardLeft`, `DashboardRight`, `DashboardNotes` | |
| 51 | `InsightCallouts` | インサイト強調 | `InsightTitle`, `InsightCallout1`, `InsightCallout2`, `InsightNotes` | |
| 52 | `ClosingCTA` | クロージング／CTA | `ClosingTitle`, `ClosingBullets`, `ClosingCTA`, `ClosingContact`, `BrandLogo` | |
| 53 | `NextActionPlan` | 次アクション計画 | `ActionHeader`, `ActionTable`, `ActionOwner`, `ActionNotes` | |
| 54 | `ContactThankYou` | 感謝ページ | `ThankTitle`, `ThankSubtitle`, `ContactInfo`, `ContactQR`, `BrandLogo` | `BackgroundImage` |
| 55 | `AppendixIndex` | 付録索引 | `AppendixList`, `AppendixNotes`, `AppendixIcon` | |
| 56 | `ComplianceSummary` | ガバナンス／コンプライアンスまとめ | `ComplianceTitle`, `ComplianceChecklist`, `ComplianceNotes` | `ComplianceIcon` |

> 上表で 56 レイアウトを提示しています。ベース 12 ページに加え、上記のうち 38 ページ以上を新たに実装して合計 50 ページ規模を構成する想定です。必要に応じて類似レイアウトを派生コピーし、アンカー名と配置を調整してください。

### 6.3 レイアウトイメージ（テキスト表現）

1. Layout: SectionCoverSimple
```
+----------------------------------------------------+
|                     SectionTitle                    |
|                   SectionSubtitle                   |
|                        (Logo)                       |
+----------------------------------------------------+
```

2. Layout: SectionCoverPhoto
```
+----------------------------------------------------+
|                 SectionTitle                        |
|               SectionSubtitle                       |
| +-----------------------------------------------+   |
| |                 HeroImage                     |   |
| +-----------------------------------------------+   |
|                    BrandLogo                     |
+----------------------------------------------------+
```

3. Layout: SectionCoverIconic
```
+----------------------------------------------------+
|  [Icon]    SectionTitle                            |
|           SectionSubtitle                          |
|                     BrandLogo                      |
+----------------------------------------------------+
```

4. Layout: SummaryExecutiveBoard
```
+----------------------------------------------------+
|                 SummaryLead                        |
+----------------------------------------------------+
| SummaryBullets (左)      | SummaryMetrics (右)      |
|  • Point                 |  KPI: 120%               |
|  • Point                 |  KPI: 98%                |
+----------------------------------------------------+
| SummaryNotes                                       |
+----------------------------------------------------+
```

5. Layout: SummaryThreeColumn
```
+----------------------------------------------------+
|                    SummaryLead                     |
+--------------------+------------------+------------+
| SummaryColLeft     | SummaryColCenter | SummaryCol |
|  • Point           |  • Point         |  • Point   |
|  • Point           |  • Point         |  • Point   |
+--------------------+------------------+------------+
| SummaryIcons / Notes                                |
+----------------------------------------------------+
```

6. Layout: SummaryKPIBoard
```
+----------------------------------------------------+
| KPIHeadline                                        |
+----------------------+-----------------------------+
| KPIPrimary           | KPISecondary                |
|  Score: 95%          |  Score: 88%                 |
+----------------------+-----------------------------+
| KPIChart                                         |
+----------------------------------------------------+
| KPIFootnote                                      |
+----------------------------------------------------+
```

7. Layout: VisionMissionStatement
```
+----------------------------------------------------+
| VisionText                                         |
+----------------------------------------------------+
| MissionText             | MissionIcon              |
+----------------------------------------------------+
| MissionNotes                                       |
+----------------------------------------------------+
```

8. Layout: BenefitCards
```
+----------------------------------------------------+
| BenefitTitle                                       |
+------------------+------------------+------------------+
| BenefitCard1     | BenefitCard2     | BenefitCard3     |
|  • Point         |  • Point         |  • Point         |
+------------------+------------------+------------------+
| BenefitIllustration                                |
+----------------------------------------------------+
```

9. Layout: OpportunitySizing
```
+----------------------------------------------------+
| OpportunityHeader                                  |
+----------------------------------------------------+
| OpportunityChart                                   |
+----------------------------------------------------+
| OpportunityNotes                                   |
+----------------------------------------------------+
```

10. Layout: SWOTMatrix
```
+------------------------+---------------------------+
| SWOTStrength           | SWOTWeakness              |
|  • Strong brand        |  • Limited budget         |
+------------------------+---------------------------+
| SWOTOpp                | SWOTThreat                |
|  • Market growth       |  • Competitors            |
+------------------------+---------------------------+
| SWOTNotes                                         |
+----------------------------------------------------+
```

11. Layout: QuadrantAnalysis
```
+------------------+------------------+
| QuadrantTL       | QuadrantTR       |
|  • Note          |  • Note          |
+------------------+------------------+
| QuadrantBL       | QuadrantBR       |
|  • Note          |  • Note          |
+------------------+------------------+
| QuadrantAxis         | QuadrantNotes |
+----------------------+----------------+
```

12. Layout: NineCellMatrix
```
+-----+-----+-----+
| A1  | A2  | A3  |
+-----+-----+-----+
| B1  | B2  | B3  |
+-----+-----+-----+
| C1  | C2  | C3  |
+-----+-----+-----+
| NineLegend | NineNotes         |
+------------+-------------------+
```

13. Layout: ProblemBeforeAfter
```
+----------------------------------------------------+
| ProblemBefore                                      |
+------------------------------+---------------------+
| Before State                 | After State         |
|  • Issue 1                   |  • Improvement 1    |
|  • Issue 2                   |  • Improvement 2    |
+------------------------------+---------------------+
| ProblemNotes (Icon)                                  |
+----------------------------------------------------+
```

14. Layout: PainGainMatrix
```
+--------------------+------------------------------+
| Pain Points        | Gains                        |
|  • Pain 1          |  • Gain 1                    |
|  • Pain 2          |  • Gain 2                    |
+--------------------+------------------------------+
| PainGainNotes                                      |
+----------------------------------------------------+
```

15. Layout: PersonaProfile
```
+----------------------+-----------------------------+
|      PersonaPhoto    | PersonaSummary              |
+----------------------+-----------------------------+
| PersonaDetails                                     |
+----------------------------------------------------+
| PersonaNeeds                                       |
+----------------------------------------------------+
```

16. Layout: JourneyMap
```
+----------------------------------------------------+
| JourneyTimeline                                    |
| Step1 -> Step2 -> Step3 -> Step4                   |
+----------------------------------------------------+
| JourneyPainPoints                                  |
|  • Friction point                                  |
+----------------------------------------------------+
| JourneyNotes                                       |
+----------------------------------------------------+
```

17. Layout: SolutionModules
```
+----------------------------------------------------+
|                 SolutionTitle                       |
|               SolutionOverview                      |
+---------------+---------------+--------------------+
| Module A      | Module B      | Module C           |
| Illustration  | Illustration  | Illustration       |
+---------------+---------------+--------------------+
| SolutionNotes                                      |
+----------------------------------------------------+
```

18. Layout: SolutionBlueprint
```
+----------------------------------------------------+
| BlueprintHeader                                    |
+----------------------------------------------------+
| BlueprintDiagram                                   |
|  [Architecture Diagram Placeholder]                |
+----------------------------------------------------+
| BlueprintNotes                                     |
+----------------------------------------------------+
```

19. Layout: PhasedImpact
```
+----------------------------------------------------+
| PhasedTitle                                        |
+----------------------------------------------------+
| Phase 1 | Benefit 1                                |
| Phase 2 | Benefit 2                                |
| Phase 3 | Benefit 3                                |
+----------------------------------------------------+
| PhasedNotes                                       |
+----------------------------------------------------+
```

20. Layout: ServiceCatalogGrid
```
+----------------------------------------------------+
| CatalogTitle                                       |
+------------------+------------------+------------------+
| Item A           | Item B           | Item C           |
|  Icon            |  Icon            |  Icon            |
+------------------+------------------+------------------+
| CatalogNotes                                      |
+----------------------------------------------------+
```

21. Layout: RoadmapQuarterly
```
+----------------------------------------------------+
|                    RoadmapTable                    |
| Q1 | Milestone | Owner | Notes                     |
| Q2 | Milestone | Owner | Notes                     |
| Q3 | Milestone | Owner | Notes                     |
| Q4 | Milestone | Owner | Notes                     |
+----------------------------------------------------+
| RoadmapMilestones           | RoadmapNotes          |
+-----------------------------+----------------------+
```

22. Layout: RoadmapVertical
```
+----------------------------------------------------+
| RoadmapTimeline                                    |
|  Milestone 1                                       |
|  Milestone 2                                       |
|  Milestone 3                                       |
+----------------------------------------------------+
| RoadmapDetails             | RoadmapNotes          |
+----------------------------+----------------------+
```

23. Layout: RoadmapSwimlane
```
+----------------------------------------------------+
| RoadmapSwimlanes                                   |
| Team A | ████ ░░░░ ▒▒▒▒                           |
| Team B | ░░░░ ████ ▒▒▒▒                           |
+----------------------------------------------------+
| RoadmapLegend               | RoadmapNotes          |
+-----------------------------+----------------------+
```

24. Layout: RoadmapJourney
```
+----------------------------------------------------+
| JourneyMilestones                                  |
|  Icon -> Step -> Icon -> Step -> Icon              |
+----------------------------------------------------+
| JourneyNotes                                       |
+----------------------------------------------------+
```

25. Layout: RoadmapGantt
```
+----------------------------------------------------+
| GanttChart                                         |
| Task A | ████████                                  |
| Task B |   ███████                                 |
| Task C |     █████                                 |
+----------------------------------------------------+
| GanttLegend               | GanttNotes             |
+---------------------------+-----------------------+
```

26. Layout: RoadmapCalendar
```
+----------------------------------------------------+
| CalendarGrid                                       |
| Mo Tu We Th Fr                                     |
| 01 02 03 04 05                                     |
| 08 09 10 11 12                                     |
+----------------------------------------------------+
| CalendarHighlights         | CalendarNotes         |
+----------------------------+----------------------+
```

27. Layout: ImplementationMilestoneWall
```
+----------------------------------------------------+
| MilestoneBoard                                     |
|  [Sticky-style milestone cards grid]               |
+----------------------------------------------------+
| MilestoneOwners            | MilestoneNotes        |
+----------------------------+----------------------+
```

28. Layout: LaunchChecklist
```
+----------------------------------------------------+
| LaunchHeader                                       |
+----------------------------------------------------+
| LaunchChecklist                                    |
|  [ ] Task 1                                        |
|  [ ] Task 2                                        |
|  [ ] Task 3                                        |
+----------------------------------------------------+
| LaunchNotes                                        |
+----------------------------------------------------+
```

29. Layout: KPIHighlight
```
+----------------------------------------------------+
| HighlightTitle                                     |
+----------------------+-----------------------------+
| HighlightPrimary    | HighlightSecondary           |
|  Metric: 120%       |  Metric: 85%                 |
+----------------------+-----------------------------+
| HighlightChart                                     |
+----------------------------------------------------+
```

30. Layout: MetricTrendComparison
```
+----------------------------------------------------+
| MetricChart                                        |
|  [Line vs Bar]                                     |
+----------------------------------------------------+
| MetricTable                                        |
| Metric | Current | Target                          |
+----------------------------------------------------+
| MetricNotes                                        |
+----------------------------------------------------+
```

31. Layout: FinancialBreakdown
```
+----------------------------------------------------+
| FinanceTable                                       |
| Cost Center | Amount | %                           |
+----------------------------------------------------+
| FinanceChart                 | FinanceNotes        |
+-----------------------------+----------------------+
```

32. Layout: FinancialScenarioTable
```
+----------------------------------------------------+
| ScenarioTable                                      |
| Base | Optimistic | Conservative                   |
+----------------------------------------------------+
| ScenarioChart                                      |
+----------------------------------------------------+
| ScenarioNotes                                      |
+----------------------------------------------------+
```

33. Layout: ResourceHeatmap
```
+----------------------------------------------------+
| ResourceMatrix                                     |
| [Heatmap grid placeholder]                         |
+----------------------------------------------------+
| ResourceLegend             | ResourceNotes         |
+----------------------------+----------------------+
```

34. Layout: ResourceAllocationStack
```
+----------------------------------------------------+
| ResourceStackChart                                 |
|  [Stacked area]                                    |
+----------------------------------------------------+
| ResourceSummary            | ResourceNotes         |
+----------------------------+----------------------+
```

35. Layout: OrgStructure
```
+----------------------------------------------------+
|                     OrgChart                       |
| (Hierarchy diagram with departments and leads)     |
+----------------------------------------------------+
| OrgNotes                         | OrgContact       |
|                                  |  • email         |
|                                  |  • phone         |
+----------------------------------------------------+
```

36. Layout: OrgOperatingModel
```
+----------------------------------------------------+
| OperatingDiagram                                   |
|  [Operating model lifecycle arrows]                |
+----------------------------------------------------+
| OperatingOwners             | OperatingNotes        |
+-----------------------------+----------------------+
```

37. Layout: RACIOverview
```
+----------------------------------------------------+
| RACIChart                                          |
| Task | Responsible | Accountable | Consulted | ... |
+----------------------------------------------------+
| RACINotes                                          |
+----------------------------------------------------+
```

38. Layout: GovernanceTimeline
```
+----------------------------------------------------+
| GovernanceTimeline                                 |
|  Month | Gate | Owner                              |
+----------------------------------------------------+
| GovernanceRoles            | GovernanceNotes       |
+----------------------------+----------------------+
```

39. Layout: ProcessSteps
```
+----------------------------------------------------+
|                  ProcessHeader                     |
+-----------+-----------+-----------+---------------+
| Step 1    | Step 2    | Step 3    | Step 4        |
|  Icon     |  Icon     |  Icon     |  Icon         |
+-----------+-----------+-----------+---------------+
| ProcessNotes                                      |
+----------------------------------------------------+
```

40. Layout: ProcessLoop
```
+----------------------------------------------------+
| ProcessLoop                                        |
|  [Circular arrows placeholder]                     |
+----------------------------------------------------+
| ProcessCaption             | ProcessNotes          |
+----------------------------+----------------------+
```

41. Layout: ProcessSwimlane
```
+----------------------------------------------------+
| ProcessSwimlane                                    |
| Lane A | [Step1] -> [Step2]                        |
| Lane B | [StepA] -> [StepB]                        |
+----------------------------------------------------+
| ProcessRoles               | ProcessNotes          |
+----------------------------+----------------------+
```

42. Layout: ChecklistBoard
```
+----------------------------------------------------+
| ChecklistHeader                                    |
+----------------------------------------------------+
| ChecklistItems                                     |
|  [ ] Item 1                                        |
|  [ ] Item 2                                        |
+----------------------------------------------------+
| ChecklistNotes                                     |
+----------------------------------------------------+
```

43. Layout: TaskKanban
```
+----------------------------------------------------+
| KanbanHeader                                       |
+------------------+------------------+------------------+
| To Do            | In Progress      | Done             |
|  • Card          |  • Card          |  • Card          |
+------------------+------------------+------------------+
| KanbanNotes                                        |
+----------------------------------------------------+
```

44. Layout: RiskMitigation
```
+----------------------------------------------------+
| RiskTable                                          |
| Risk | Impact | Probability | Mitigation           |
| ...                                                |
+----------------------------------------------------+
| RiskNotes               | RiskIcon                 |
+----------------------------------------------------+
```

45. Layout: IssueLogBoard
```
+----------------------------------------------------+
| IssueTable                                         |
| Issue | Owner | Status | Due                       |
+----------------------------------------------------+
| IssueNotes                                         |
+----------------------------------------------------+
```

46. Layout: FAQCards
```
+----------------------------------------------------+
| FAQTitle                                           |
+----------------------+-----------------------------+
| Q1 / Answer          | Q2 / Answer                 |
| Q3 / Answer          | Q4 / Answer                 |
+----------------------+-----------------------------+
| FAQIllustration             | FAQNotes             |
+-----------------------------+----------------------+
```

47. Layout: SupportContactSheet
```
+----------------------------------------------------+
| SupportChannels                                    |
|  • Email                                           |
|  • Phone                                           |
|  • Portal                                          |
+----------------------------------------------------+
| SupportIcon                | SupportNotes          |
+----------------------------+----------------------+
```

48. Layout: DataComboChart
```
+----------------------------------------------------+
| ChartPrimary (Bar + Line combo)                    |
| ChartSecondary (Legend / Breakdown)                |
+----------------------------------------------------+
| ChartNotes                                         |
+----------------------------------------------------+
```

49. Layout: DataHeatmap
```
+----------------------------------------------------+
| Heatmap                                            |
| [Gradient grid]                                    |
+----------------------------------------------------+
| HeatmapLegend             | HeatmapNotes           |
+---------------------------+-----------------------+
```

50. Layout: DataDashboardSplit
```
+----------------------------------------------------+
| DashboardLeft             | DashboardRight         |
|  • Metric cards           |  • Charts              |
+----------------------------------------------------+
| DashboardNotes                                      |
+----------------------------------------------------+
```

51. Layout: InsightCallouts
```
+----------------------------------------------------+
| InsightTitle                                       |
+------------------+------------------+------------------+
| InsightCallout1  | InsightCallout2  | InsightCallout3  |
|  “Quote / key”   |  “Data point”    |  “Action”        |
+------------------+------------------+------------------+
| InsightNotes                                      |
+----------------------------------------------------+
```

52. Layout: ClosingCTA
```
+----------------------------------------------------+
| ClosingTitle                                       |
| ClosingBullets                                     |
|  • Step 1                                          |
|  • Step 2                                          |
+----------------------------------------------------+
| CTA Button              | Contact Info | BrandLogo |
+----------------------------------------------------+
```

53. Layout: NextActionPlan
```
+----------------------------------------------------+
| ActionHeader                                       |
+----------------------------------------------------+
| ActionTable                                        |
| Task | Owner | Due | Status                        |
+----------------------------------------------------+
| ActionNotes                                        |
+----------------------------------------------------+
```

54. Layout: ContactThankYou
```
+----------------------------------------------------+
| ThankTitle                                         |
| ThankSubtitle                                      |
+----------------------------------------------------+
| ContactInfo                | BrandLogo             |
|  • Email                   |                        |
|  • Phone                   |                        |
+----------------------------------------------------+
| ContactQR                                          |
+----------------------------------------------------+
```

55. Layout: AppendixIndex
```
+----------------------------------------------------+
| AppendixList                                       |
|  1. Appendix A                                     |
|  2. Appendix B                                     |
+----------------------------------------------------+
| AppendixNotes                                      |
+----------------------------------------------------+
```

56. Layout: ComplianceSummary
```
+----------------------------------------------------+
| ComplianceTitle                                    |
+----------------------------------------------------+
| ComplianceChecklist                                |
|  [ ] Policy A                                      |
|  [ ] Policy B                                      |
+----------------------------------------------------+
| ComplianceNotes             | ComplianceIcon       |
+-----------------------------+----------------------+
```

```
参考 Layout: Two Columns
+----------------------------------------------------+
|                     Heading                         |
+-----------------------------+-----------------------+
|         Left Content        |     Right Content     |
|  • Point                    |   • Point             |
|  • Point                    |   • Point             |
+-----------------------------+-----------------------+
|                        Footer                       |
+----------------------------------------------------+
```

### 6.4 既存レイアウトとの共存
- 既存の `Title`, `Two Column Detail`, `Timeline Detail` などはそのまま残す。  
- 新レイアウト群はマスター内でグループ化し、分かりやすい順番で並べ替えて構わない。  
- 共通で利用するアンカー（例: `BrandLogo`, `SectionTitle`）は他レイアウトとの整合性を優先。

### 6.5 納品時に必要なもの
- 更新済み `samples/templates/templates.pptx`。  
- 追加レイアウトとアンカー名の一覧（上表との差分があれば注記）。  
- 追加が必要なダミー画像／アイコン（PNG/SVG）をまとめたフォルダ（任意）。  
- 変更メモ（レイアウト追加数、既存レイアウト調整の有無）。

以上の内容で PPTX 編集を実施いただければ、こちらで抽出・サンプル更新・テストを続行できます。
