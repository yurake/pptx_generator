---
title: RM-020 LibreOffice PDF 変換検証
created: 2025-10-25
roadmap_item: RM-020 PDF 自動生成対応
status: done
---

## 概要
- LibreOffice 導入後の headless 実行確認として PPTX 生成と PDF 変換を同時に実施した。
- CLI 統合テスト `tests/test_cli_integration.py` を追加の検証として実行し、26 件すべて成功した。
- LibreOffice バージョンは `25.8.2.2` であることを `soffice --headless --version` で確認した。

## 実行コマンド
```bash
uv run pptx gen samples/json/sample_jobspec.json --template samples/templates/templates.pptx --export-pdf
uv run --extra dev pytest tests/test_cli_integration.py
soffice --headless --version
```

## 出力およびログ
- PPTX: `.pptx/gen/proposal.pptx`
- PDF: `.pptx/gen/proposal.pdf`
- 付随ログ: `.pptx/gen/analysis.json`, `.pptx/gen/rendering_log.json`, `.pptx/gen/monitoring_report.json` などが更新された。
- モニタリングアラート: 9 スライドで注意事項が発生。既知のテンプレート仕様に起因する警告であり、後続作業でのトリアージ対象とする。
- Rendering Warnings: 18 件。現状のサンプルでは許容範囲内であることを確認済み。

## 所見
- LibreOffice を介した PDF 出力はエラーなく完了し、`.pptx/gen/proposal.pdf` が生成された。
- CLI 統合テストはすべて成功し、LibreOffice 導入に伴う回帰は見られなかった。
- 今後 CI へ反映する際は `UV_CACHE_DIR=.uv-cache` を併用する運用を runbook に追記する必要がある。

## 生成物レビュー
- `.pptx/gen/rendering_log.json` にてレンダリング時間 93ms、警告 18 件（うち 17 件が空プレースホルダー）であることを確認。サンプル仕様上、未使用プレースホルダーが残る構成であり許容範囲と判断。
- `.pptx/gen/monitoring_report.json` では 9 スライド全てが警告対象となり、`margin` 5 件と `grid_misaligned` 2 件が Analyzer で検知された。Polisher 無効のため改善差分はなく、既知のレイアウト起因として次期テンプレート調整時に見直す。
- `analysis.json` / `analysis_pre_polisher.json` の集計値は一致し、Analyzer の再解析で悪化は見られなかった。

## 次のアクション
特になし（生成物レビュー済み）。
