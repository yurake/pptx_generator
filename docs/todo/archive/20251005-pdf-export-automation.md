---
目的: レンダリング後に PPTX を自動で PDF 化し、配布用資料を確実に生成できるようにする
担当者: Codex
関連ブランチ: feat/pipeline-pdf-export
期限: 2025-10-25
---
関連Issue: #56

- [x] CLI に `--export-pdf` オプションを追加し、LibreOffice を利用した変換フローを実装する
  - メモ: PATH に `soffice` が無い場合のフォールバックとエラーメッセージを設計する
- [x] CLI オプションの UX 定義を行い、`docs/design/overview.md` に反映する
  - メモ: `--export-pdf` 単独実行／`--export-pdf=only` の選択肢を評価し、互換性を記載する
- [x] パイプラインへ PDF 生成ステップを追加し、`outputs` ディレクトリへ保存する
  - メモ: 変換所要時間・失敗時の再実行戦略を検討する
- [x] 変換ジョブのリトライポリシーとタイムアウトを設定し、監査ログへ記録する
  - メモ: LibreOffice のエラーコードを分類し、再実行対象／即時失敗を切り分ける
- [x] テストケースを整備し、PDF 出力の存在確認とページ数検証を自動化する
  - メモ: `pypdf` などの依存追加を検討し、テスト時の LibreOffice 有無を切り替えられるようにする
- [x] テスト環境で LibreOffice が利用できない場合のモック戦略を用意する
  - メモ: 既存の `analysis.json` を活用し、モック PDF を生成するスクリプトを検討する
- [x] ドキュメント更新
  - メモ: README と運用ガイドに PDF 出力手順と前提条件（LibreOffice 依存）を明記する
- [x] 運用 Runbook に、失敗時の復旧フローと連絡手順を追記する
- [x] QA 観点のチェックリストを作成し、社内レビューを実施する
  - メモ: 期待する PDF 品質（フォント埋め込み、ページ番号、余白）を明示する
- [x] PR 作成
  - メモ: [docs/notes/pr/feat-pdf-export-automation.md](../notes/pr/feat-pdf-export-automation.md) にドラフト記載。レビューア割当と最終リハーサル完了後に GitHub PR 化予定

## メモ
- 背景整理ノート: [docs/notes/issues/0008-pdf-export-automation.md](../notes/issues/0008-pdf-export-automation.md)
- Java Runtime 未導入時の挙動を事前確認する
- LibreOffice のバージョンアップに伴う互換性の影響を把握しておく
- LibreOffice 依存を回避する代替 API（Microsoft Graph 等）をバックアップ案として調査する

