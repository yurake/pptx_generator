# Template AI マルチプロバイダ対応方針（2025-11-23）

## 1. 背景
- Stage1 テンプレ抽出では Template AI による usage_tags 推定を既定挙動としているが、現状は `mock` / `openai` 対応に限定されている。
- Stage2/Stage3（Content AI / Layout AI）は `PPTX_LLM_PROVIDER` を通じて OpenAI / Azure OpenAI / Anthropic Claude / AWS Bedrock（Claude）など複数プロバイダを切り替え可能。
- 本番環境では Azure OpenAI を標準採用する想定があり、Stage1 だけが別プロバイダ縛りだと環境差異による品質ギャップが発生する。

## 2. 現状整理
| 機能 | 対応プロバイダ | 主な実装 | 備考 |
| --- | --- | --- | --- |
| Template AI | `mock`, `openai` | `src/pptx_generator/template_ai/client.py` | `PPTX_TEMPLATE_LLM_PROVIDER`（未設定時は `PPTX_LLM_PROVIDER`）を参照するが、分岐自体は限定的。 |
| Content AI | `mock`, `openai`, `azure-openai`, `anthropic`, `aws-claude` | `src/pptx_generator/content_ai/client.py` | Responses/Chat API ラッパーを切り替える実装が存在。 |
| Layout AI | 同上 | `src/pptx_generator/layout_ai/client.py` | プロンプト・レスポンス形式は JSON 固定で共通化済み。 |

Template AI だけが以下の問題を抱えている:
1. プロバイダ分岐が OpenAI 固定であり、Azure / Anthropic / Bedrock が選択不可。
2. policy / diagnostics が `mock` / `openai` 前提で設計されている。
3. README や設計ドキュメントがプロバイダ差異を説明していない。

## 3. 目標
- Template AI でも OpenAI / Azure OpenAI / Anthropic Claude / AWS Bedrock（Claude）を選択できるようにする。
- プロンプトテンプレートや policy 設定でモデル・デプロイメントを制御できるようにし、ドキュメントへ設定手順を明記する。
- diagnostics に推論プロバイダやエラー情報を残し、監査性を確保する。

## 4. 対応方針
1. **クライアント共通化**  
   - Content/Layout AI で実装済みのクライアント抽象化を Template AI へ移植し、共通レスポンス解析を導入する。
   - 応答が JSON でない場合はフォールバック（ヒューリスティック）へ切り替えつつ、警告ログで検知できるようにする。

2. **設定項目整理**  
   - `PPTX_TEMPLATE_LLM_PROVIDER` を優先して解決し、未指定時は `PPTX_LLM_PROVIDER` を流用する現行仕様を維持。
   - policy JSON (`config/template_ai_policies.json`) で `provider` / `model` / `temperature` / `max_tokens` を上書きできるようにし、Azure の `deployment` や AWS の `modelId` を指定可能にする。
   - README / requirements / design ドキュメントにプロバイダ毎の必要環境変数（`OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `ANTHROPIC_API_KEY`, `AWS_REGION` など）を追記する。

3. **テスト・検証**  
   - 各プロバイダをモックした単体テストを追加し、環境変数でクライアントが切り替わることを確認する。
   - `uv run --extra dev pytest tests/test_template_ai.py` を回帰テストとして実行。外部依存を必要とするテストは環境変数未設定時に skip できるように設計する。

4. **ドキュメント更新**  
   - README（CLI チートシート）と Stage1 の設計・要件ドキュメントへ、対応プロバイダと設定手順を記載する。
   - 必要に応じて runbook や policy にプロバイダ別の手順を追加する。

## 5. 作業分解
1. Template AI クライアントのリファクタリング（共通 LLM クライアント化、プロバイダ追加）。
2. Policy JSON / diagnostics 更新。
3. ドキュメント改訂（README, design, requirements 等）。
4. テスト追加・回帰実行。

## 6. リスク
- Azure / Anthropic / Bedrock が JSON 以外の応答形式を返した場合、解析が失敗する可能性がある。→ 例外処理とフォールバックを強化。
- 依存パッケージ（`openai`, `anthropic`, `boto3`）未導入環境向けにわかりやすいエラーメッセージを維持する。
- 既存環境変数との競合を避けるため、環境変数の優先順位と既定値を明示する。

## 7. 次のアクション
1. 新規ブランチ `feat/rm070-template-ai-providers` を作成し、上記リファクタリングを実装する。
2. policy とドキュメントを更新し、テストを整備する。
3. PR 作成前に ToDo / ロードマップとの整合を確認し、issue #302 に進捗を共有する。
