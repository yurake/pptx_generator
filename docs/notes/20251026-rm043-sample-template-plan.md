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
