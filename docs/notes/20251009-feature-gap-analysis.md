# 機能実装状況ギャップ調査（2025-10-09）

## 調査概要
- 目的: 既存実装とロードマップ／ToDo の整合を確認し、必須機能の抜け漏れを洗い出す。
- 対象: CLI パイプライン、レンダラー／アナライザー実装、`docs/requirements/requirements.md` と `docs/design/design.md` の記載、公開中の ToDo／ロードマップ。

## 確認できた主な実装
- CLI はバリデーション→リファイン→レンダリング→簡易アナライザー→PDF 変換のステップを実行し、監査ログを出力（`src/pptx_generator/cli.py:182` 付近）。
- レンダラーはタイトル・箇条書き・表・画像・グラフを描画し、アンカー未指定時はフォールバック座標を使用（`src/pptx_generator/pipeline/renderer.py:88`）。
- アナライザーは入力 JSON を基に箇条書きレベルやフォントサイズ、コントラスト、画像余白を検査し `analysis.json` を生成（`src/pptx_generator/pipeline/analyzer.py:62`）。
- PDF 変換は LibreOffice を呼び出すステップを内蔵し、タイムアウト／リトライ制御と `PPTXGEN_SKIP_PDF_CONVERT` フラグをサポート（`src/pptx_generator/pipeline/pdf_exporter.py:31`）。

## 必須機能の抜け漏れ（優先提案）
- **サブタイトル／ノートの描画対応**
  - 要件ではスライドごとの文章要素を扱う前提だが、レンダラーは `Slide.title` のみ描画し `subtitle` や `notes` を利用していない（`src/pptx_generator/pipeline/renderer.py:105` 付近、`samples/json/sample_jobspec.json:17`）。
  - サブタイトルが未反映のままになるため、基本レイアウト要件を満たすよう描画処理を追加する。
- **TextBox 要素のスキーマ・実装不足**
  - 設計書では `slides[].textboxes[]` を必須想定（`docs/design/design.md:96`）だが、Pydantic モデルやレンダラーに対応がない（`src/pptx_generator/models.py:89`）。
  - スキーマ整合性のためモデル拡張と描画実装、サンプル／テスト整備が必要。
- **アナライザーの対象が PPTX ではなく JSON**
  - 要件では PPTX の実体を解析することが明記されている（`docs/requirements/requirements.md:28`）が、現実装は入力 JSON を走査している（`src/pptx_generator/pipeline/analyzer.py:62`）。
  - レイアウト崩れ検知や `grid_misaligned` 等の診断（`docs/design/design.md:136`）が実現できず、品質指標に直結するため、PPTX 解析ステップの実装が急務。
  - 2025-10-15 更新: RM-013 の実装で PPTX 実体を解析し、余白・グリッド・フォント・コントラストを計測する `analysis.json` を出力するよう対応済み。
- **自動補正（Refiner/Polisher）の適用範囲不足**
  - Refiner が適用するのは箇条書きレベル再調整のみで、フォント引き上げや色補正は提案止まり（`src/pptx_generator/pipeline/refiner.py:25`）。要件では安全な補正の自動適用を求めている（`docs/requirements/requirements.md:31`）。
  - `.NET` 製 Polisher（Open XML SDK）も未実装で、設計ドキュメントの構成と乖離（`docs/design/design.md:155`）。段落間隔や禁則調整など仕上げ工程が欠落している。
- **通知／配布チャネルの未整備**
  - 生成成果物の通知や保存先連携は要件に含まれる（`docs/requirements/requirements.md:34`）が、実装や ToDo が存在しない。
  - ロードマップでも `Service-F Distributor` をバックログ扱いにしており（`docs/roadmap/roadmap.md:128`）、優先度再評価が必要。

## ロードマップ・ToDo への提案
- 上記ギャップに対応する ToDo を追加し、レンダラー強化を RM-012、PPTX 解析アナライザーを RM-013、自動補正拡張を RM-014 として管理する。
- アナライザーと Polisher の実装方針は `docs/design/design.md` と齟齬が大きいため、RM-013 / RM-014 の設計アップデートと同時にタスク化する。
- 通知／配布や運用要件（監査ログ連携など）は RM-004 とバックログ項目（Service-F Distributor）に紐付け、優先度の再評価とロードマップ追記で共有する。

## 次のアクション案
1. RM-012: レンダラーでサブタイトル・ノート・テキストボックス描画を追加し、サンプルとテストを拡張。
2. RM-013: PPTX 解析ベースのアナライザー PoC を実装し、`grid_misaligned` など設計上必須の診断項目を有効化。
3. RM-014: Refiner の適用ルール拡張と Open XML SDK Polisher のプロジェクト雛形作成。
4. 配布フロー（通知・保存）の実装計画を立案し、ロードマップ優先度を更新。
