# ブリーフポリシー廃止調査メモ（2025-11-05）

## 背景
- 工程2 `uv run pptx prepare` で `config/brief_policies/default.json` を読み込み、`BriefAIOrchestrator` へ渡しているが、外部ファイルによる骨子制御を廃止したいという議論があったため現状を確認。

## 調査結果
- CLI の `prepare` コマンドは `DEFAULT_BRIEF_POLICY_PATH = config/brief_policies/default.json` を固定参照し、`load_brief_policy_set` で読み込んだポリシーを `BriefAIOrchestrator.generate_document()` に渡している（`src/pptx_generator/cli.py:55`, `src/pptx_generator/cli.py:1395-1415`）。
- `BriefAIOrchestrator` はポリシーに基づいて `resolve_story_phase`／`resolve_chapter_title` を実行し、`BriefCard` の章タイトル・ストーリーフェーズを決定するとともに `BriefStoryContext` を生成する（`src/pptx_generator/brief/orchestrator.py:54-137`）。工程3以降はこの `story_context` を前提に章順を扱う。
- `--brief-policy` オプションは削除済みで、CLI からポリシーを切り替える手段は存在しない。現状は「固定ファイルを必ず読み込み、骨子を決める」挙動となっている。
- ドキュメント上でも `config/brief_policies/default.json` が工程2の前提として記載されており、CLI 仕様・要件ドキュメント双方が依存している（例: `docs/design/cli-command-reference.md`, `docs/requirements/stages/stage-02-content-normalization.md`）。
- RM-054（静的テンプレ統合）では Blueprint から slot 単位の骨子を扱う構想があるが、現時点では工程2への具体的な組み込みが未実装。Blueprint を導入しない限り、`prepare` はポリシーに頼って章順・story_phase を決定している。

## 代替案・課題
- ポリシーをコード内の定数へ内製化し、外部ファイルを廃止する（CLI 互換性維持）。ただし story_phase・章タイトルの変更容易性が低下するため、後続の RM-054 やテンプレ運用と整合させる設計が必要。
- 工程2で生成する骨子をテンプレ Blueprint（RM-054）や JobSpec から自動導出するフローを設計し、ポリシー機能を Blueprint へ移管する。
- RM-054 と連動させる場合、静的テンプレ Blueprint から `story_context` を生成する設計を先に確立し、動的モードでのデフォルト骨子（introduction/problem/…）も Blueprint 互換の形で保持する必要がある。
- ドキュメントとテスト（`docs/design/cli-command-reference.md` など）でポリシーファイルを前提にしている箇所を更新する必要がある。

## 結論
- 現時点では `config/brief_policies/default.json` が `prepare` の必須依存であり、policy を廃止すると story_phase/章タイトル/ストーリーフェーズの決定が失われる。`RM-054` の静的テンプレ統合で Blueprint を導入する設計が固まるまでは、policy か同等の骨子定義が必要。
- `config/brief_policies/default.json` の廃止は、Blueprint や JobSpec から骨子を導出する新フローと同時に実施するのが望ましい。ロードマップ項目（RM-058）で、RM-054 との依存関係を踏まえた検討を進める。
