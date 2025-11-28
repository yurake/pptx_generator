# stage 3 入力と生成AI呼び出し単位の確認（2025-11-05）

## 背景
- 「stage 3 の入力として stage 2 が出力する `jobspec.json` が必要か」「生成AIをページ単位・カード単位のどちらで呼び出すか」という議論に対応するため、現行実装と今後のロードマップ整合を確認した。

## 調査結果
- stage 2 `uv run pptx prepare` は `prepare_card.json`（PrepareCard 群）や `prepare_story_outline.json` などを生成するが、`jobspec.json` は出力しない。ジョブスペックは外部から与えるか、テンプレ抽出（stage 1）で得られるスキャフォールドを別途整形する必要がある。
- stage 3 `uv run pptx compose` は引数 `spec_path` に指定した JobSpec を `_load_jobspec()` で検証し、必須フィールド `meta.title`／`auth` や Slide 要素のスキーマ一致を要求する（`src/pptx_generator/cli.py:1815-1908`）。stage 2 の成果物だけでは要件を満たさない。
- 現在のテンプレ抽出結果 (`TemplateExtractorStep.build_jobspec_scaffold`) は `JobSpecScaffold` を出力しており、`JobSpec` に不足するフィールドや `placeholders` など余剰プロパティを含む（`src/pptx_generator/pipeline/template_extractor.py:266-321`）。このギャップ解消を RM-057 で扱っている。
- `PrepareAIOrchestrator.generate_document()` は入力プレペアの各章（カード）を順に処理し、`SlideAIOrchestrator` を経由して LLM をカード単位で呼び出す構成に更新済み。ログ (`prepare_ai_log.json`) にはカードごとのモデル名・警告・トークン数が記録される。
- 旧コンテンツ生成フロー（`SlideAIOrchestrator`）は JobSpec のスライドごとに `LLMClient.generate()` を呼んでいたため、AI 呼び出し単位は「スライド（=カード）単位」が基本であり、デッキ全体を一度に生成する設計ではない。

## 結論
- stage 3 の JobSpec 入力は stage 2 の成果物のみでは充足されず、外部で整備した JobSpec（または RM-057 によるスキャフォールド→JobSpec 変換）が必要。
- 生成AIの呼び出しはカード（章・スライド）単位を前提としており、RM-054 の静的テンプレ統合でも slot/カード単位の生成に整合させる方針が必要。
- 動的テンプレでは `jobspec` なしで柔軟に話数を組み立てる必要があるため、LLM 連携時も「デッキ全体を一度に生成するモード」とカード単位生成の双方を切り替え可能にする設計が求められる。
- ポリシー／Blueprint 連携の再設計（RM-054, RM-058）と JobSpec 整合（RM-057）を組み合わせ、stage 2→stage 3 のデータ受け渡しを段階的に統一する。
