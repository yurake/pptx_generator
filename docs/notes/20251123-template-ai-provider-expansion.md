# Template AI プロバイダ拡張方針メモ（2025-11-23）

## 1. 背景と課題
- Template AI は `mock` / `openai`（Responses API）にのみ対応し、Content AI / Layout AI がサポートする `azure-openai`・`anthropic`・`aws-claude` などを利用できない。
- Stage2/Stage3 は `PPTX_LLM_PROVIDER` を通じて複数プロバイダを切り替えられる設計になっており、Stage1 だけが制約付きだと本番環境（例: Azure OpenAI 標準運用）との構成差異が生まれる。
- RM-064 では Stage1 メタデータと Stage3 の整合を進めているため、Template AI 側も共通プロバイダ設計へ統一する必要がある。

## 2. 現状整理（2025-11-23 時点）
| 機能 | 対応プロバイダ | 主な実装 | 備考 |
| --- | --- | --- | --- |
| Template AI | `mock`, `openai` | `src/pptx_generator/template_ai/client.py` | `PPTX_TEMPLATE_LLM_PROVIDER`（未設定時は `PPTX_LLM_PROVIDER`）を参照するが、分岐は限定的で Responses API 固定。 |
| Content AI | `mock`, `openai`, `azure-openai`, `anthropic`, `aws-claude` | `src/pptx_generator/content_ai/client.py` | プロバイダごとに専用クライアントを実装済み。 |
| Layout AI | 同上 | `src/pptx_generator/layout_ai/client.py` | JSON 応答ベースで共通クライアントを切り替える設計。 |

Template AI 側で不足している要素:
1. プロバイダ解決が実質 `mock` / `openai` に固定されている。
2. Content/Layout AI に存在する Azure OpenAI / Anthropic / AWS Bedrock のクラス・ユーティリティが流用されていない。
3. policy JSON（`config/template_ai_policies.json`）にプロバイダ別デプロイメントやモデル情報を設定できる項目が不足している。
4. README や設計ドキュメントに Template AI のプロバイダ差異が十分説明されていない。

## 3. 目標
- Template AI でも OpenAI / Azure OpenAI / Anthropic Claude / AWS Bedrock（Claude）といった Stage2/Stage3 と同等の LLM を選択できるようにする。
- policy 設定と環境変数でモデルやデプロイメントを制御可能にし、ドキュメントに設定手順を明記する。
- `diagnostics.json.template_ai` などの監査メタに推論プロバイダやエラー情報を残す。

## 4. 対応方針
1. **クライアント層の共通化**  
   - Content/Layout AI の LLM クライアント抽象化を Template AI へ移植し、共通レスポンス解析とエラーハンドリングを導入する。  
   - JSON 以外の応答や拒否が発生した場合はヒューリスティックへフォールバックし、ログに明示する。

2. **設定項目の拡張**  
   - `PPTX_TEMPLATE_LLM_PROVIDER` を優先し、未設定時は `PPTX_LLM_PROVIDER` を利用する現行仕様を維持。  
   - `config/template_ai_policies.json` で policy 単位に `provider` / `model` / `temperature` / `max_tokens` などを上書き可能にし、Azure（deployment）や AWS（modelId）など固有設定を扱えるようにする。  
   - README、`docs/design/stages/stage-01-template-pipeline.md`、`docs/requirements/stages/stage-01-template-pipeline.md` 等に必要な環境変数（`OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `ANTHROPIC_API_KEY`, `AWS_REGION` など）と手順を追記する。

3. **テスト整備**  
   - `tests/test_template_ai.py` にプロバイダ選択テストを追加し、環境変数の切り替えで想定クライアントが生成されることを確認する。  
   - 既存モックレスポンス検証を維持しつつ、新規クライアント導入時の例外パスをスモークテストする。

4. **段階的リリース**  
   - 初期対応では Azure OpenAI を優先し、Anthropic / AWS Bedrock の導入は段階的に進める。  
   - `diagnostics.json.template_ai` にプロバイダ名・モデルを記録し、実運用での確認を容易にする。

## 5. 作業分解案
1. 共通クライアント抽象化（`content_ai.client` からユーティリティを切り出し Template AI に適用）。
2. Template AI ファクトリのプロバイダ分岐拡張（Azure → Anthropic → AWS の順で導入）。
3. policy JSON と diagnostics のスキーマ更新。
4. README / design / requirements / runbook の更新。
5. テスト更新と CI 通過確認。

## 6. リスクと考慮事項
- Azure / Anthropic / Bedrock が返す応答フォーマット差異を吸収できるか事前に確認する。
- Template AI は JSON 応答を前提としているため、プロンプト／ガードを調整しフォールバック経路を用意する。
- 依存パッケージ（`openai`, `anthropic`, `boto3` など）が未導入の環境向けに、分かりやすい例外メッセージを維持する。
- レート制限やコスト面の影響を把握し、Stage3 の切り替えと同時に検証するロードマップを整備する。

## 7. 次のアクション
1. 共通クライアント抽象化の PoC ブランチを作成し、Template AI から Azure クライアントを呼び出せることを検証する。
2. 必要な作業範囲を整理し、新規 RM（例: RM-071）および ToDo を整備する。完了後は ToDo をアーカイブ（`docs/todo/archive/20251123-rm071-template-ai-providers.md`）へ移動。
3. README / design / requirements の更新方針をまとめ、レビュー後に順次反映する。
