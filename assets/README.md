# assets ディレクトリ運用ガイド

## 目的
- ロゴや図版などのブランド資産を一元管理し、ドキュメントや CLI サンプルから再利用しやすい状態を保つ。
- 機微情報を含まないサンプル資産のみを配布し、公開リポジトリへ誤って実データをコミットしないようガバナンスを整える。
- 将来的な自動生成ワークフロー（Mermaid 図レンダリング等）と連動できるフォルダ構成・命名規則を明文化する。

## フォルダ構成
- `pptx_generator_logo_white.png` / `pptx_generator_logo_black.png`: README や資料に掲載するロゴ画像（背景色に応じた 2 種）。
- `logo.pptx`: ロゴ配置を検証するための最小 PPTX。レンダリングテストやテンプレ検証の補助に利用。
- `diagrams/`（予定）: Mermaid などのソースを `diagrams/mermaid/` に、生成画像を `diagrams/png/` へ配置する想定。`docs/notes/20251105-mermaid-render-automation.md` を参照。
- その他のサブディレクトリを追加する場合は、本 README に目的と構造を追記すること。

## 命名規則とファイル種別
- ファイル名は用途が分かる英語スネークケースとし、ブランド名など固有情報は含めない（例: `demo_timeline.png`）。
- 画像形式は PNG / SVG を推奨。PowerPoint 連携を検証する場合のみ `.pptx` を許可する。
- バージョン差分が必要な場合はサフィックスで管理する（例: `pptx_generator_logo_white_v2.png`）。履歴管理は Git に依存するため、巨大ファイルは避ける。
- 生成スクリプトがある場合は `scripts/` 配下に配置し、この README からリンクする。

## 更新フロー
1. 追加・更新する資産の目的と利用先を ToDo に記録し、本 README の該当箇所を先に更新する。
2. 機微情報を含まないことを確認し、匿名化が必要な場合はダミー素材へ差し替える。
3. 参照元ドキュメント（例: `README.md`, `docs/runbooks/*.md`, サンプル JSON）で相対パスが有効かを確認する。
4. 画像を生成したスクリプト・コマンドがあれば `docs/notes/` や `docs/runbooks/` に手順を記録し、再現性を担保する。
5. PR では差分プレビューやスクリーンショットを添付し、レビューアが用途を把握できるようにする。

## セキュリティと運用上の注意
- 実案件のロゴ・写真・ブランド設定など機微情報は配置しない。必要な場合は匿名化したサンプルを作成し `samples/assets/` へ移す。
- `.env` や資格情報は厳禁。外部ツールのベンダーロゴなどライセンスに制約がある素材もコミットしない。
- LibreOffice や .NET 等に依存する変換を行った場合は、バージョン差異が影響しないか確認し、必要なら `docs/policies/config-and-templates.md` へ追記する。

## 関連ドキュメント
- `docs/AGENTS.md`: ドキュメント更新全般のガイドライン。
- `docs/policies/config-and-templates.md`: 設定・テンプレート変更時のポリシー。
- `docs/notes/20251105-mermaid-render-automation.md`: Mermaid 図自動レンダリング構想。
- `docs/roadmap/roadmap.md#rm-063-assets-運用ガイド整備`: 本テーマのロードマップ項目。

