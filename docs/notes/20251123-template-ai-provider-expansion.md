# Template AI プロバイダ拡張方針メモ（2025-11-23）

## 1. 背景と課題
- Template AI は `mock` / `openai`（Responses API）にのみ対応し、Content AI / Layout AI がサポートする `azure-openai`・`anthropic`・`aws-claude` などを利用できない。
- プロジェクト全体では `PPTX_LLM_PROVIDER` を基点に複数プロバイダへ切り替える運用を想定しており、Stage1 だけが制約付きだと本番環境での構成差異（例: Azure OpenAI を標準使用）に適合できない。
- RM-064 では Stage1 メタデータと Stage3 の整合を進めているため、Template AI 側も共通プロバイダ設計へ統一する必要がある。

## 2. 現状整理（2025-11-23 時点）
| 機能 | 対応プロバイダ | 実装ファイル | 備考 |
| --- | --- | --- | --- |
| Template AI | `mock`, `openai` | `src/pptx_generator/template_ai/client.py` | Responses API 固定。`PPTX_TEMPLATE_LLM_PROVIDER` 未設定時は `PPTX_LLM_PROVIDER` を参照。 |
| Content AI | `mock`, `openai`, `azure-openai`, `anthropic`, `aws-claude` | `src/pptx_generator/content_ai/client.py` | ラッパーを切り替えるファクトリ実装。各プロバイダごとに専用クライアントを実装済み。 |
| Layout AI | 同上 | `src/pptx_generator/layout_ai/client.py` | `PPTX_LLM_PROVIDER` を基点に共通実装を利用。 |

Template AI で不足している要素:
1. プロバイダ解決の条件式が `mock` / `openai` に限定されている。
2. Content/Layout AI に存在する Azure OpenAI / Anthropic / AWS Bedrock のクラス・ユーティリティが Template AI 側に共有されていない。
3. policy JSON (`config/template_ai_policies.json`) にプロバイダ別デプロイメント指定やモデル名の整理がなく、OpenAI 固定の前提になっている。
4. README / ドキュメントの手順が Template AI のプロバイダ差異を説明していない。

## 3. 対応方針案
1. **クライアント層の共通化**
   - `content_ai`・`layout_ai` で実装済みの LLM クライアント群（OpenAI/Azure/Anthropic/AWS）を Template AI でも再利用できるよう、共通モジュールへ切り出す。
   - Template AI 特有の分類リクエスト（payload, prompt 生成）は保持しつつ、実際の API 呼び出しは共通クライアントで行う。

2. **設定項目の拡張**
   - 環境変数は `PPTX_TEMPLATE_LLM_PROVIDER` を優先し、Fallback で `PPTX_LLM_PROVIDER` を見る現行仕様を維持。
   - プロバイダごとのモデル/デプロイメント指定は `config/template_ai_policies.json` の policy 単位で上書きできるようにし、Azure 用の `deployment` / `api_version`、Anthropic 用の `model` などを設定可能にする。
   - README / `docs/design/stages/stage-01-template-pipeline.md` / `docs/requirements/stages/stage-01-template-pipeline.md` に、対応プロバイダと必要な環境変数を追記する。

3. **テスト整備**
   - `tests/test_template_ai.py` にプロバイダ選択の分岐テストを追加し、`PPTX_TEMPLATE_LLM_PROVIDER` を切り替えた際に想定クライアントが生成されることを検証。
   - 既存のモックレスポンス検証を維持しつつ、新規クライアント導入時に行うべきスモークテストを追加（例: Azure クライアント初期化の例外ハンドリング）。

4. **段階的リリース**
   - 初期実装では Azure OpenAI を優先導入し、Anthropic/AWS は後続タスクでの追加でも可。
   - `diagnostics.json.template_ai` にプロバイダ情報（model / deployment など）を追記し、実運用時に利用状況を把握できるようにする。

## 4. 作業分解案
1. 共通クライアントの抽象化（`content_ai.client` から共通ユーティリティを切り出す）。
2. Template AI ファクトリのプロバイダ分岐を拡張し、Azure クライアントを追加。
3. policy JSON の schema 更新（deployment / model 設定項目の追加）。
4. ドキュメント更新（README, design, requirements, runbook）。
5. テスト更新と CI 通過確認。

## 5. RM / ToDo 提案
- RM-064 の子タスクでは範囲が大きいため、新規 RM（例: **RM-066 Template AI マルチプロバイダ対応**）を追加し、Stage1 のプロバイダ整合性を担当。
- `docs/todo/YYYYMMDD-rm066-template-ai-providers.md` を作成し、上記作業分解案をチェックリスト化。
- RM-064 の ToDo には「Template AI プロバイダ整合性の確認」タスクを記録済みなので、実装に移る段階で RM-066 とリンクさせる。

## 6. リスクと考慮事項
- Azure / Anthropic / Bedrock の API 仕様は Content/Layout AI 実装依存のため、Template AI へ流用する際に JSON 応答フォーマットの差異が出ないか確認が必要。
- Template AI は JSON スキーマ固定で応答を期待するため、応答フォーマットに制限を加えるテンプレートが実装できるか事前検証が必要（特に Anthropic / Bedrock）。
- 実運用で Template AI を Azure に切り替える場合は Rate Limit やコストの影響を精査する必要があるため、Stage3 との同時切替を想定したロードマップを検討する。

## 7. 次のアクション
1. 共通クライアント抽象化の PoC ブランチを作成し、Template AI で Azure クライアントを呼び出せることを最小構成で検証。
2. 作業範囲が確認でき次第、RM-066 をロードマップへ追加し、詳細 ToDo を作成。
3. README / design / requirements へのドキュメント更新は PoC 成果を踏まえて反映。
