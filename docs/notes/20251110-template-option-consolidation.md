# CLI テンプレートオプション削減の検討

## 背景
- `pptx gen` は統合により `--template` オプションを廃止し、`generate_ready.json.meta.template_path` を必須とする仕様へ移行した。
- `pptx compose` / `pptx mapping` には依然として `--template` オプションが残り、未指定時は `jobspec.meta.template_path` などからテンプレートを解決する。
- ユーザーから、`compose` と `mapping` でも `--template` を削除し、テンプレ参照は成果物に埋め込む形へ統一したいという要望があった。

## 現状の挙動
- `compose` / `mapping` は `_resolve_template_path` を通じてテンプレートパスを決定しており、オプション優先 → jobspec → カレントディレクトリというフォールバックを持つ。
- テンプレート情報は工程4/5の成果物 (`generate_ready.json`) に書き込まれ、`gen` 実行時に参照される。
- 現在も CLI 実行時には `generate_ready.json` にテンプレートパスが埋め込まれるため、工程間の整合性は確保されている。

## 課題
- `compose` / `mapping` が `--template` を受け付けることで、工程1のテンプレート抽出・ジョブスペック整備と独立にテンプレファイルを差し替え可能だが、運用ルール上は `jobspec.meta.template_path` へ正規化する方向にある。
- `--template` を残すと `generate_ready.json` とテンプレ実体が乖離するリスクがあり、統合後の運用ポリシーとも矛盾する。
- CLI オプション表記や README の説明もこの仕様変更に追従しておらず、旧来の手動指定フローが混在している。

## 要件（提案）
- `compose` / `mapping` から `--template` オプションを削除し、テンプレート解決は `jobspec.meta.template_path`（および工程1成果物）に一本化する。
- スクリプト実行時にテンプレ情報が存在しない場合は明確なエラーメッセージを出し、`pptx template` → `jobspec/meta` へ流すフローを促す。
- ドキュメント（CLI リファレンス、README、docs/design/cli-command-reference.md 等）を更新し、テンプレ指定の新方針を周知する。
- テストでは `--template` 不在での正常系／エラー系を検証し、`generate_ready.json` への埋め込みが確実に行われることを確認する。

## 次ステップ案
- 新規 RM（仮称: RM-066 CLI テンプレ指定統一）を起票し、`compose` / `mapping` の CLI から `--template` を削除する改修を追跡する。
- エラーメッセージやドキュメント更新、既存スクリプトへの影響調査を含むタスクを `docs/todo/` で管理する。
