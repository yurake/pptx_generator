---
目的: 初期パイプラインの骨組みを用意し、開発を開始できる状態にする
担当者: Codex
関連ブランチ: feat/initial-setup
期限: 2025-10-11
関連Issue: #1
---

- [x] Python パッケージ構成の雛形作成
  - メモ: validator / renderer / analyzer などのモジュール分割を準備
- [x] CLI エントリポイントの追加
  - メモ: JSON 入力と出力パス指定の受け口を実装
- [x] 設定ファイルの初期値作成
  - メモ: branding / rules のダミー設定を配置
- [ ] レビュー対応
  - メモ: 指摘事項はここに記載

## メモ
- 依存ライブラリは最小限 (pydantic, typer, python-pptx) から導入する。
- validator 拡張後に `uv run --extra dev pytest` を実行し、テスト成功を確認。
