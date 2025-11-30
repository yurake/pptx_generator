# RM-084 リファクタリング優先候補調査メモ（2025-02-16）

## 背景
- CLI とパイプライン各 Stage の主要モジュールに大規模で複雑な関数が散見され、可読性・保守性の悪化を招いている。
- リファクタリング候補を洗い出し、ロードマップに新規テーマとして追加するための調査結果をまとめる。

## 調査対象と所見
- `src/pptx_generator/cli.py`
  - 全体で約 3,600 行に達し、サブコマンドごとのエントリポイントからファイル入出力、パイプライン実行、成果物書き出しまでが 1 つに集中している。
  - `prepare` コマンド実装（`src/pptx_generator/cli.py:2029`）が 190 行超にわたり、例外処理・テンプレ探索・AI オーケストレーション・成果物集約が混在している。
  - CLI 側を引数解析と orchestration 呼び出しに限定し、stage ごとのハンドラへ委譲する構造化が必要。
- `src/pptx_generator/pipeline/mapping.py`
  - `MappingStep.run`（281 行）がカード並び替え、レイアウトスコアリング、テーブルアンカー解決、容量制御、成果物生成を一括で扱っている。
  - 状態を示すローカル変数が多く、副作用が散在しているためステップ別ヘルパーとデータクラス化で責務を分離したい。
- `src/pptx_generator/pipeline/draft_structuring.py`
  - `_build_document`（226 行）がセクション構築、AI 推薦の集計、ログ生成をクロージャ内でまとめて処理している。
  - DraftSection 生成、AI 統計集計、レコメンドログ整備を別コンポーネントへ切り出すことで保守性向上が見込める。
- `src/pptx_generator/prepare_ai/orchestrator.py`
  - `_build_cards_static`（223 行）が Blueprint 展開、章割り当て、LLM プロンプト生成、応答検証、カード変換までを単一メソッドで行う。
  - スロット割り当てやプロンプト構築、LLM 応答検証を個別関数・クラスへ分割し、副作用を減らす余地が大きい。
- `src/pptx_generator/layout_validation/suite.py`
  - `_build_layout_records`（265 行）がアンカー走査、ヒューリスティック評価、AI 呼び出し、警告集約を複雑な辞書操作で処理している。
  - プレースホルダー解析・usage tag 判定・警告生成を専用ビルダーに分離し、データモデル化することで読みやすさを改善できる。
- `src/pptx_generator/api/app.py`
  - `create_app`（280 行超）が FastAPI ルート定義を 1 関数内に保持し、依存取得とエラーハンドリングが重複している。
  - 機能別ルーター分割や共通レスポンス生成ユーティリティ化による分離が望ましい。

## 次のアクション（案）
1. CLI とパイプライン各 Stage の責務分割案を設計し、orchestrator インターフェイスを整理する。
2. Mapping / Draft Structuring / Prepare AI 周辺の長大メソッドを段階的に分割し、テスト観点を整備する。
3. FastAPI ルートを cards・logs など機能単位の router へ切り出し、共通処理をユーティリティ化する。

## 参照ログ
- 収集日: 2025-02-16
- 調査担当: Codex CLI
