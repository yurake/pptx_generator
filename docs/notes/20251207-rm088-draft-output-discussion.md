ユーザー: 「現在 docs/todo/20251207-rm088-template-slide-priority.md の ##メモ にあるUATを実施中。pptx composeで --draft-output を廃止したく、廃止による影響を調査して」
エージェント: 「`pptx compose` の CLI 実装とハンドラを確認したところ、`--draft-output` がドラフト成果物（`draft_draft.json` など）や DraftStore の出力先を指定しており、外部フックへ渡す環境変数 `PPTX_DRAFT_OUTPUT` にも利用されている。テスト類やドキュメント、サンプルでも tmp ディレクトリを使う際に明示指定しているため、そのまま廃止すると多方面に影響がある」
ユーザー: 「オプションを廃止というよりは、--outputがあるんだからそっちの指定に合わせてほしい、という意味の方が強い」
エージェント: 「`--output` に追随する形にするなら、`draft_output = output_dir / \"draft\"` のように内部で導出し、`PPTX_DRAFT_OUTPUT` へもその値を渡す対応が考えられる。同時に `pptx mapping` も揃え、テスト・ドキュメントも `--draft-output` 前提を外す必要あり。静的モードや外部フックは変換後のパスを参照するので互換性を保てる」
ユーザー: 「そもそもなぜdraftフォルダが必要なんだっけ？composeだけじゃダメ？」
エージェント: 「アウトライン実行で `draft_draft.json` や `draft_review_log.json` を出力し、マッピング実行も DraftStore を介して再利用するため。HITL 差戻しや静的パススルー処理もこのディレクトリ構造を前提にしているので、ドラフト成果物を専用ディレクトリに分離する設計になっている」
ユーザー: 「では --draft-output は廃止、出力先を compose/draft にするのは？」
エージェント: 「`--output` のサブディレクトリとして `draft` を固定すれば設計意図を保てる。デフォルトでは `.pptx/compose/draft` になり、外部フックも `PPTX_DRAFT_OUTPUT` にそのパスを渡せば動作する。ドキュメントはあるべき姿だけ記載すれば良い」
ユーザー: 「既存利用者はいないため後方互換の心配によるドキュメント記載は不要。あるべき姿の情報だけ記載。storeはcompose/draft/storeになる？」
エージェント: 「`draft_store_dir` は `draft_output / \"store\"` のままなので `<output>/draft/store` になる」
ユーザー: 「ok, これを前提に対応しよう。ここまでの議論をnotesに転記して。要約などせずディスカッションした内容を記録するため」
