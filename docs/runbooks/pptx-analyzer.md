# PPTX アナライザー運用手順

## 目的
- `analysis.json` を用いてスライド品質の課題（フォントサイズ不足、コントラスト低下、グリッドずれ、余白逸脱など）を特定し、修正判断を支援する。
- RM-013 に基づきレンダリング済み PPTX を実体解析し、`issues` / `fixes` を出力するステップを標準化する。
- 解析結果を Refiner・HITL レビュー・通知フローへ連携し、改善作業のログを追跡可能にする。

## 前提条件
- Python 3.12 系の仮想環境で `uv sync` 済み。
- LibreOffice（PDF 変換時）および .NET 8 SDK（仕上げツール連携時）がインストール済み。
- `config/branding.json` とテンプレートが最新化され、レンダラーが図形 ID／アンカー名を付与できる状態。
- `docs/notes/20251015-pptx-analyzer.md` に記録された実装メモを参照し、対象バージョンに差異がないことを確認する。
- プロジェクト全体の工程配置は README の「アーキテクチャ概要」に掲載している工程図で事前に確認しておく。

## 実行手順
1. 解析対象 JSON を用意する  
   - `samples/json/sample_jobspec.json` をベースに案件仕様を整備し、必要に応じてブランド設定 (`config/branding.json`) やテンプレート (`templates/*.pptx`) を指定する。
2. CLI でレンダリングと解析を実行する  
  - まず工程4で `generate_ready.json` を用意する（未実施の場合）:
    ```bash
    uv run pptx compose samples/json/sample_jobspec.json \
      --content-approved .pptx/content/content_approved.json \
      --draft-output .pptx/draft \
      --output .pptx/gen \
      --template templates/<brand>/<version>/template.pptx
    ```
  - 工程5（レンダリング）を実行し、Analyzer 結果を取得する:
    ```bash
    uv run pptx gen .pptx/gen/generate_ready.json \
      --branding config/branding.json \
      --output .pptx/gen \
      --export-pdf
    ```
  - 工程4の成果物を点検済みであっても、最終出力を更新する際は `pptx gen` を再実行する。
   - `analysis.json` は `--output` で指定したディレクトリに保存される。既定値は `.pptx/gen/analysis.json`。
   - Review Engine 連携用に `review_engine_analyzer.json` も併せて出力される。設計と一致しない場合は CLI バージョンを確認する。
   - `--export-pdf` は任意。LibreOffice が利用できない場合は外してもよい。
3. 実行ログを確認する  
   - CLI 出力に `Analysis: <path>` と `ReviewEngine Analysis: <path>` が表示されることを確認する。
   - `Audit: <path>` のログ（`audit_log.json`）にステップの開始・終了と処理時間が記録される。

## 出力物の読み方
- `analysis.json` の構造（主要項目のみ抜粋）
  ```json
  {
    "meta": {...},
    "slides": <int>,
    "issues": [
      {
        "id": "issue-...",
        "type": "grid_misaligned",
        "severity": "warning",
        "message": "...",
        "target": {"slide_id": "...", "element_id": "...", "element_type": "..."},
        "metrics": {...},
        "fix": {"id": "fix-...", "type": "move", "payload": {...}}
      }
    ],
    "fixes": [...]
  }
  ```
- 主な issue / fix 種別
  | issue.type | 概要 | 主な fix.type |
  | --- | --- | --- |
  | `font_min` | フォントサイズが最小基準を下回る | `font_raise` |
  | `contrast_low` | 背景色とのコントラスト比不足 | `color_adjust` |
  | `bullet_depth` | 許容段落レベルを超過 | `bullet_cap` |
  | `layout_consistency` | 直前段との段差が大きい | `bullet_reindent` |
  | `margin` | 画像がスライド余白に接近・はみ出し | `move` |
| `grid_misaligned` | グリッド（0.125in）へスナップできていない | `move` |
- Severity は `info` / `warning` / `error` を想定。`error` は必ず対処し、`warning` はテンプレ側の意図と照合して判断する。
- `review_engine_analyzer.json` の概要
  ```json
  {
    "schema_version": "1.0.0",
    "generated_at": "...",
    "slides": [
      {
        "slide_id": "agenda",
        "grade": "B",
        "issues": [{"code": "font_min", "message": "...", "severity": "warning"}],
        "autofix_proposals": [
          {
            "patch_id": "fix-font",
            "description": "...",
            "patch": [{"op": "replace", "path": "/slides/1/bullets/0/items/0/font/size_pt", "value": 20.0}]
          }
        ],
        "notes": {"unsupported_fix_types": ["move"]}
      }
    ]
  }
  ```
  - `grade` は Analyzer `severity` に基づき `A` / `B` / `C` を付与。
  - Auto-fix 変換は箇条書きレベル調整・フォントサイズ・文字色のみ対応。それ以外の Fix は `notes.unsupported_fix_types` に記録する。

## 運用フロー
1. `analysis.json` を参照し、`issues` の `target.slide_id` / `element_id` を起点に差戻し対象を抽出する。
2. `mapping_log.json` の `meta.analyzer_issue_count` と各スライドの `analyzer` セクションを確認し、`font_min` や `contrast_low` など補完トリガー候補の優先度を整理する。
3. 自動修正可能な `fixes` は Refiner または HITL で適用可否を判断する。適用時は `audit_log.json` に記録する。
4. テンプレ構造の問題が疑われる場合は `docs/notes/20251015-pptx-analyzer.md` の既知課題を確認し、必要に応じて `docs/todo/` にフォローアップタスクを追加する。
5. 重大な診断結果は Issue (#162 など) へ転記し、再発防止の設計変更を検討する。

## トラブルシューティング
- **`analysis.json` が生成されない**: レンダリングに失敗している可能性がある。`Audit` のログや CLI エラーを確認し、テンプレや spec の整合を見直す。
- **図形が特定できない**: テンプレートでアンカー名を変更した場合は JSON の `anchor` を同期させる。`SlideSnapshot` は図形名や ID を使用するため、命名変更があると紐付けが切れる。
- **余白検出の閾値が合わない**: `config/rules.json` の `analyzer.margin_in` を調整し、ブランドガイドラインに適合させる。値を変更した場合は `docs/policies/config-and-templates.md` に理由を記録する。
- **大規模スライドで時間がかかる**: 処理時間を `audit_log.json` に記録し、性能改善の検討事項として `docs/notes/` に追記する。必要であれば `uv run --extra dev pytest -k analyzer` で個別テストを行う。

## 参考資料
- `docs/notes/20251015-pptx-analyzer.md`: 実装概要と既知課題。
- `docs/design/stages/stage-03-content-normalization.md`: Review Engine 連携仕様と Auto-fix 対応範囲。
- `docs/requirements/requirements.md`: 品質診断に関する要件。
- `tests/test_analyzer.py`: 解析結果の期待動作をカバーする単体テスト。
- `README.md` / `AGENTS.md`: CLI 使い方とタスク管理ポリシー。
