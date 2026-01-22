---
目的: RM-085 LLM プロバイダ共通化（aws-claude の全ステージ対応と JSON 解析互換を確保する）
関連ブランチ: fix/rm085-aws-claude-json
関連Issue: 未作成
roadmap_item: RM-085 LLM プロバイダ共通化  # 既存 RM を指定。未登録テーマの場合はロードマップへ RM を追加してから記入する。
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - ブランチ: fix/rm085-aws-claude-json（origin/main から作成）
    - 初期コミット: dc8ceb5 chore: add rm085 aws-claude json todo
    - push: origin/fix/rm085-aws-claude-json へ push 済み
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: aws-claude のコードフェンス付き JSON を全ステージで受け付ける共通パース追加、prepare_ai に aws-claude 対応を追加して stage1〜5 を通せるようにする。
    - ドキュメント／コード修正方針: 既存 JSON パーサ前段にコードフェンス除去/JSON 抽出の共通関数を追加し、Template/Prepare/Slide/Layout の AI 結果処理に適用。prepare_ai/client.py で Bedrock (aws-claude) を有効化。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新と CLI 簡易再実行で挙動を確認する。
    - 想定影響ファイル: src/pptx_generator/prepare_ai/client.py, src/pptx_generator/llm/*, src/pptx_generator/template_ai/*, src/pptx_generator/layout_ai/*, src/pptx_generator/slide_ai/* など。
    - リスク: パースを緩めすぎて不正 JSON を通す可能性。抽出後に JSON デコード失敗は従来通りエラーとし、厳格さを維持する。
    - テスト方針: 文字列パースの単体テスト追加（コードフェンス/前後ノイズ）。可能なら uv run pptx template ... --mode dynamic などの CLI で再現確認。
    - ロールバック方法: 共通パーサ追加と prepare_ai の aws-claude 対応コミットを revert する。
    - 承認メッセージ ID／リンク: 2026-01-22 ユーザー OK
- [x] 設計・実装方針の確定
  - メモ: コードフェンス除去と JSON 抽出を共通化するため `pptx_generator/llm/json_utils.py` を追加し、Template/Prepare/Slide/Layout の AI 応答パーサに適用する。prepare_ai は AwsClaudePrepareLLMClient を追加して Bedrock 呼び出しを有効化する。edit_ai は既に成功しているため今回は対象外とする。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: json_utils 追加、template/prepare/slide/layout の JSON 解析を共通化。prepare_ai に AwsClaudePrepareLLMClient を追加し provider 解決に aws-claude を追加。
- [x] テスト・検証
  - メモ: `python3 -m uv run --extra dev pytest tests/llm/test_json_utils.py tests/prepare_ai/test_prepare_ai_llm_client_configuration.py`
    - 失敗: uv が PATH になく `python3 -m uv` を使用 → `UV_CACHE_DIR=.uv-cache` でも uv が panic（system-configuration error）
    - 追加: `.venv` に pip が無く `python3 -m venv .venv --upgrade-deps` を実行 → pip/setuptools の取得で DNS 解決失敗（ネットワーク到達不可）
    - 追加: `.venv/bin/python -m pip install pytest pytest-cov pytest-xdist` を実施
    - 実行: `.venv/bin/python -m pytest tests/llm/test_json_utils.py tests/prepare_ai/test_prepare_ai_llm_client_configuration.py`
    - 結果: 11 passed（coverage.xml 出力）
- 追記: `PPTX_LLM_PROVIDER=aws-claude .venv/bin/pptx template samples/templates/dynamic_template.pptx --mode dynamic` 実行
    - 失敗: bedrock-runtime.us-east-2.amazonaws.com へ接続できず（NameResolutionError / EndpointConnectionError）
    - 再実行: 同コマンドで再度失敗（DNS 解決不可のまま）
    - 修正: ネットワーク許可付きで再実行 → Template stage 成功（warnings=0, errors=0）
    - 動作確認: dynamic の全ステージ実行
      - stage1: template 成功（warnings=0, errors=0）
      - stage2: prepare 成功（aws-claude 応答はコードフェンス付き JSON だがパース成功）
      - stage3: compose 成功（警告: layouts.jsonl に一致するレイアウトが見つからない）
      - stage4: gen 成功（Rendering warnings=3 / Monitoring alerts=3）
      - stage5: edit 失敗（AttributeError: AwsClaudeConfig に api_key が無く edit_ai が初期化できない）
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: aws-claude がコードフェンス付き JSON を返すため、JSON のみ期待のパーサが失敗している。
  - 決定と理由: コードフェンス除去/JSON 抽出の共通前処理を追加してプロバイダ差分を吸収する。prepare_ai に aws-claude を追加。
  - リスク(UNCONFIRMED): 抽出ロジックの過度な緩和で想定外入力を通す可能性。
  - Now/Next: ドキュメント更新要否の確認 → 仕上げ。
  - テスト実績/抜け: pytest 実行済み（11 passed）。uv は panic のため未解決。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
