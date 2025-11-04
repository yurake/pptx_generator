# 2025-10-26 RM-040 初期計画メモ

## 背景
- RM-040「コンテンツ生成AIオーケストレーション」の着手に伴い、工程3で AI 生成ドラフトを扱う仕組みを最小構成で整備する。
- 既存の `pptx prepare` コマンドは承認済みデータまたは外部ソース取り込みのみを前提としていたため、AI 生成モードを追加する。

## 決定事項
- ポリシー定義は `config/content_ai_policies.json` に集約し、`default_policy_id` を CLI で利用する。
- プロンプト定義は `src/pptx_generator/content_ai/prompts.py` で管理し、ポリシーからは `prompt_id` を参照する。
- オーケストレーション層は `src/pptx_generator/content_ai/` に専用モジュールを新設し、モック LLM クライアントを通じて本文（40 文字×最大 6 行）を生成する。
- CLI オプション追加案（`--ai-policy` / `--ai-policy-id` など）は一旦見送り、既定ポリシー固定で生成する方針へ変更する。`--content-source` との排他制御は継続検討。
- 生成結果は `content_draft.json`（`ContentApprovalDocument` 形式）、`content_ai_log.json`（プロンプトと警告の監査ログ）、`ai_generation_meta.json`（ポリシー・ハッシュ情報）の 3 ファイルを標準出力物とする。

## 追加検討事項
- 実サービスの LLM 接続と API 認証方式。暫定実装では `MockLLMClient` を利用するため、外部通信は発生しない。
- 禁則語や機密情報フィルタリングのルール強化。`safeguards` セクションに記録し、将来の Review Engine 連携時に enforcement する。
- `audit_log.json` への AI 生成メタ連携と、レビュー後との差分比較ロジック（`content_hash` を起点に再生成判定を行う）。
- Review Engine / Analyzer との統合: 生成結果に対する初回レビュー自動呼び出しは本タスクの範囲外のため、後続 ToDo で検討する。

## 参照
- `docs/design/stages/stage-03-content-normalization.md`
- `docs/requirements/stages/stage-03-content-normalization.md`
- `docs/todo/20251026-rm-040-ai-orchestration.md`
