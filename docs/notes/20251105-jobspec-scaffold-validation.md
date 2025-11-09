# ジョブスペックスキャフォールド検証メモ（2025-11-05）

## 背景
- `.pptx/extract/jobspec.json` を `uv run pptx compose` の入力として流用した際に `meta.title` / `auth` 欠如や `slides[].placeholders[]` の余剰プロパティが原因でバリデーションエラーになる、との指摘を受け事実確認を実施。

## 調査結果
- テンプレ抽出 (`pptx template`) は `TemplateExtractorStep.build_jobspec_scaffold` を通じて `JobSpecScaffold` を生成しており、出力項目は `schema_version` や `template_path` 等のテンプレ設計向けメタ情報に限定されている（`src/pptx_generator/pipeline/template_extractor.py:266-321`）。
- モデル定義上も `JobSpecScaffold` は `meta.title` や `auth` を持たない（`src/pptx_generator/models.py:205-251`）。
- スライド配列は `placeholders` 配下にアンカー座標などのテンプレ情報を保持する。
- 一方、`pptx compose` は `_load_jobspec` で `JobSpec.parse_file` を呼び、`JobSpec` モデルで厳密検証を行う（`src/pptx_generator/cli.py:568-600`）。
- `JobSpec` は `meta.title` や `auth` を必須とし（`src/pptx_generator/models.py:149-199`）、`Slide` は `model_config = ConfigDict(extra="forbid")` により未定義プロパティ（`placeholders` など）を許可しない（`src/pptx_generator/models.py:149-167`）。
- 実際に `.pptx/extract/jobspec_bk.json` を確認すると、`meta` にテンプレ由来フィールドのみが含まれ `auth` が欠如しているほか、各スライドが `placeholders` を保持している（再現例）。
- そのため、抽出直後の `jobspec.json` をそのまま `pptx compose` に渡すと、`missing`（必須フィールド不足）および `extra_forbidden`（未許可フィールド）エラーが発生することを確認した。

## まとめ
- テンプレ抽出成果物は設計補助用のスキャフォールドであり、工程3で求められる `JobSpec` とはスキーマが異なる。
- `uv run pptx compose` の入力として利用するには、`meta.title` / `auth` の補完や `placeholders` → `textboxes` 等への正規化を行う変換ステップが必要。
- 抽出 CLI で生成する `jobspec.json` と `pptx compose` 入力スキーマを統一するためのロードマップ項目が必要。


補足:
feat/047-draft-structuring での調査結果

- uv run pptx compose samples/extract/jobspec.json --template samples/templates/templates.pptx --brief-cards samples/prepare/prepare_card.json を実行すると、meta.title と auth の欠如、および slides[].sequence / slides[].placeholders の extra_forbidden によりバリデーションが失敗しました（エラーログ抜粋付き、現行ブランチで再現）。
- JobSpec は meta.title と auth を必須とし、Slide は model_config = ConfigDict(extra="forbid") で未定義プロパティを禁止しているため、抽出直後の JSON をそのまま読み込むと上記エラーになります (src/pptx_generator/models.py:149-201)。
- テンプレ抽出側の build_jobspec_scaffold はテンプレ設計情報のみに特化した JobSpecScaffold を出力しており、meta.title や auth を付与せず、placeholders 情報を保持したままにしています (src/pptx_generator/pipeline/template_extractor.py:266-316)。
- samples/extract/jobspec.json も同じスキーマ構造で、meta にテンプレ系フィールドのみが入り、各スライド配下に placeholders が残っているため、現在の pptx compose 入力要件を満たしていません (samples/extract/jobspec.json)。

次のアクション候補

1. スキャフォールドを正式な JobSpec へ整形する変換ステップの設計・実装。
2. もしくはテンプレ抽出成果物と compose 入力スキーマ統合に向けたロードマップ項目の起票。

## 2025-11-08 更新
- `pptx_generator.spec_loader.load_jobspec_from_path` を導入し、テンプレ抽出 `jobspec.json` を読み込んだ際に `JobSpecScaffold` を `JobSpec` へ自動変換する処理を追加。
- 変換時はテンプレプレースホルダから `Slide.textboxes` を生成し、タイトル／サブタイトルの初期値や非テキスト要素の要約を `notes` に残す。
- CLI (`pptx compose` / `pptx mapping`) は従来どおり `_load_jobspec` を経由するため、テンプレ抽出直後の `jobspec.json` でもバリデーションエラーなく実行できる。
