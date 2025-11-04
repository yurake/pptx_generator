---
title: generate_ready メタ情報と監査ログ連携メモ
created: 2025-11-09
tags:
  - cli
  - pipeline
  - roadmap:RM-049
---

## 目的
- `generate_ready.json` にテンプレート参照やマッピングメタを埋め込み、工程5専用の `pptx gen` で追加オプションなしにテンプレートを解決できるようにする。
- 監査ログ (`audit_log.json`) に工程4のメタ情報を確実に残し、再実行時のトレーサビリティを担保する。

## 追加したメタ情報
- `meta.template_path`: マッピング時に指定したテンプレートへの絶対／相対パス。CLI 側では generate_ready と同一ディレクトリを基点に解決するフォールバックを実装。
- `meta.template_version`: テンプレート抽出時のバージョン識別子。監査ログでも `mapping.template_version` として保持。
- `meta.generated_at`: 生成タイムスタンプを ISO8601 UTC で記録。監査ログの `mapping.generate_ready_generated_at` に引き継ぐ。
- `meta.content_hash`: コンテンツ整合性チェック用のハッシュ値。今回 CLI では未使用だが、監査ログに残して再レンダリング時の差分検知に活用予定。

## CLI (`pptx gen`) 側の対応
- `GenerateReadyDocument` をロードして `template_path` が欠落している場合は Exit Code 2 で警告、再マッピングを促す。
- `mapping_log.json` が存在する場合は `meta` セクションを監査メタに統合し、`maps` のフェールバック回数や AI 修正件数を記録。
- 旧 `--template` / `--content-approved` 系オプションを削除し、`generate_ready` と `--branding` のみで工程5を完結させる。

## 監査ログへの反映
- `mapping_meta` をベースアーティファクトとしてレンダリングパイプラインに渡し、`mapping` セクションに以下を確保：
  - `generate_ready_path`
  - `generate_ready_generated_at`
  - `template_version`
  - `template_path`
  - `fallback_count` / `ai_patch_count` など `mapping_log.json` 由来の統計
- ブランド設定はテンプレートから抽出した場合でも `branding.source.template` にテンプレートパスを格納。

## 残検討事項
- `meta.content_hash` を工程5で活用し、レンダリング後のプレゼンハッシュと突合する仕組み。
- 監査ログの `mapping.slides` に generate_ready のスライド数を復活させるか、`mapping_log.json` の統計から充足可能かを判断。
- 監査ログと `.pptx/compose/mapping_log.json` の保管ポリシー整備（保持期間やアーカイブ先）。

## ToDo 連携
- `docs/todo/20251102-rm049-pptx-gen-scope.md` の「generate_ready 詳細設計」配下から本メモを参照し、追加検討はこのメモに追記する。
- 次アクションで監査ログ整備を進める際は、本メモを更新して決定事項を反映する。
