RM-081 フォント/文字容量ディスカッションログ

user
RM-081 に着手して

assistant
参照済みドキュメント:
- `docs/policies/context-engineering.md`
- `CONTRIBUTING.md`
- `docs/policies/task-management.md`
- `docs/roadmap/roadmap.md` (RM-081)
- `docs/requirements/stages/stage-03-compose.md`
- `docs/design/schema/stage-03-mapping.md`
- `docs/todo/20251124-rm081-text-capacity.md`

Plan（承認待ち）:
1. モデル／スキーマ整備  
   - `src/pptx_generator/models.py` に `TextCapacity` などの新フィールドを追加し、`JobSpecScaffoldPlaceholder`・`SlideTextbox` へ `text_capacity` を持たせる。  
   - `docs/design/schema/stage-03-mapping.md` と関連要件ドキュメントへフィールド追加の仕様を追記する。  
   - 影響範囲: JobSpec/GenerateReady 双方向変換、Renderer/Analyzer など `SlideTextbox` 参照箇所。

2. 文字数推定ロジックの共通化  
   - `src/pptx_generator/utils/` 配下に推定ヘルパーを新設し、幅・高さから `max_lines`/`max_chars` を算出する処理を集約。  
   - `src/pptx_generator/pipeline/template_extractor.py` でテキスト系プレースホルダーに `text_capacity` を計算して埋め込み、JobSpecScaffold へ出力する。  
   - 新規ユニットテストで代表寸法から期待値を検証。

3. layout_validation 連携  
   - `src/pptx_generator/layout_validation/schema.py` / `suite.py` を更新し、同じヘルパーを用いてプレースホルダー単位の `text_capacity` を JSON レコードへ付与しつつ、既存 `text_hint` の集計値もこのヘルパー出力から計算する。  
   - 既存レコード生成テストを更新し、差分確認用に追加の期待値を組み込む。

4. JobSpec 変換・テスト・サンプル更新  
   - `src/pptx_generator/spec_loader.py` と `src/pptx_generator/generate_ready.py` で `text_capacity` を取り扱うようにし、Scaffold→JobSpec 変換時に SlideTextbox へ伝播。  
   - `tests/template_audit/test_template_extractor_jobspec_output.py` や `tests/layout_validation/*` など関連テスト、サンプル JSON を更新。  
   - ドキュメント（requirements/design/roadmap/ToDo メモ）に実装結果・利用方法を反映。

想定影響ファイル:
- `src/pptx_generator/models.py`, `spec_loader.py`, `pipeline/template_extractor.py`
- `src/pptx_generator/layout_validation/{schema.py,suite.py}`
- 新規ヘルパー（例: `src/pptx_generator/utils/text_capacity.py`）
- テスト一式、docs（requirements/design/roadmap/todo）

リスク:
- 既存 JSON スキーマ互換性（古い JobSpec/GenerateReady を読む経路）が壊れる可能性。→ 新フィールドは任意扱いにし後方互換を確保。
- 推定ロジックの定数が不正確だと CLI 既存の text_hint と乖離する。→ 共通ユーティリティ化と単体テストで検証。
- layout_validation 出力フォーマット変更により既存ツールチェーンが壊れる恐れ。→ スキーマ更新とテストで担保し、ドキュメントへ明記。

テスト方針:
- `uv run --extra dev pytest tests/template_audit/test_template_extractor_jobspec_output.py`
- `uv run --extra dev pytest tests/layout_validation`
- 可能なら `tests/pipeline/render/test_renderer_rich_content.py` など SlideTextbox を使う広めのスイートを一括実行。

ロールバック方法:
- `git revert` で関連コミットを巻き戻し、docs/todo へ理由を記録すれば元のスキーマ/挙動へ戻せる。

user
承認の前に仕様を教えて
オブジェクトの情報を抽出したときに、そのオブジェクトで予定されている文字サイズの情報も取れるんだっけ？

assistant
現状のテンプレ抽出では、プレースホルダーごとに保持している情報は `anchor` / `kind` / `placeholder_type` / 図形サイズ（インチ単位の `bounds`）/ サンプル文字列 / 注記などで、フォント情報は含まれていません。モデル定義も `JobSpecScaffoldPlaceholder` に `font_size` 系フィールドを持っておらず（`src/pptx_generator/models.py:706` 付近）、テンプレ抽出処理でもそのような値は設定していません（`src/pptx_generator/pipeline/template_extractor.py:421-465`）。

文字数目安を出す必要がある箇所（`layout_validation` など）では、図形の幅・高さから固定係数で「行数」「文字数」を推定しているだけで、実際のフォントサイズを利用していません。推定ロジックは `_derive_text_hint` 内で高さ/0.28inch ≒ 行数、幅*20 ≒ 行あたり文字数として積算しています（`src/pptx_generator/layout_validation/suite.py:835-853`）。

したがって、「予定されている文字サイズ」をテンプレ抽出結果から直接取得する仕組みはまだありません。フォントサイズを扱いたい場合は、抽出段階でプレースホルダーの `TextFrame` から `FontSpec` を読み取り、`JobSpecScaffoldPlaceholder` などへ追加する実装が別途必要になります。

user
branding.json でのフォント情報保持は廃止しましょう。テンプレート作者が決めたフォントに合わせることを前提とします。

assistant
了解しました。現状は `branding.json` の `body_font` / `title_font` を各所（Renderer、Analyzer、Refiner、CLI 設定）で参照し、テンプレ抽出側はフォント情報を保持していません。ご要望に沿うには以下を進める必要があります。

- テンプレ抽出 (`TemplateExtractor`) で各プレースホルダーの `FontSpec`（フォント名／サイズ／色）を取得し、`JobSpecScaffoldPlaceholder` や Blueprint に埋め込む。
- Scaffold→JobSpec 変換や `SlideTextbox` 生成でその `FontSpec` を保持し、Renderer・Analyzer など滑らかに参照できるようモデルを拡張する。
- `branding.json` に定義されているフォント設定を段階的に廃止し、テンプレ提供値をデフォルトとする（テンプレ側に値が無い場合のフォールバック設計は別途必要）。
- 既存の `min_font_size` など規則ファイルは、テンプレフォントを前提にした検証・補正ルールへ調整する。

フォントサイズ・色などをテンプレ側に一本化する際、以下の点の方針を確認させてください。
1. テンプレ内でフォント指定が欠落しているプレースホルダー（図形）にはどの値を適用すべきか。テンプレの既定値（Theme Font）を取得して補完するのか、それともグローバルなデフォルト値を残すのか。
2. `branding.json` 自体は完全削除で問題ないか（他用途のフィールドを利用している箇所があるため、段階的移行が必要）。
3. Multi-language／ブランド差し替え対応をどう扱うか。テンプレ毎にフォントが変わる前提で、CLI からフォントを差し替える手段は不要か。

上記が整理でき次第、改めて Plan を更新し承認フローへ進めます。

user
1. テンプレの既定値（Theme Font）を取得して補完
2. 完全削除をいずれ目指している。今回はフォント情報を完全に削除する段階移行。
3. テンプレがブランドそのものになるので、外部から強制的にブランドを差し替える対応も廃止

assistant
承知しました。現状は `branding.json` からフォント設定を参照しているコードパス（CLI 設定、Renderer、Analyzer、Refiner 等）を除去し、テンプレ抽出由来のフォントをデフォルトとする前提へ移行します。Theme Font 欠落時はテンプレートのテーマ情報から解決し、どうしても取得できない場合のみフォールバック値を使います。

user
これに加えて元の依頼（プレースホルダーに含めれる文字数の取得と活用）もスコープであっているよね？

assistant
はい、スコープに含めています。今回の作業は

- プレースホルダー抽出時にテンプレ既定フォント（Theme Font を含む）を取得・保持し、以降の JobSpec/Renderer で活用すること
- そのフォント情報を前提に、各プレースホルダーが許容できる文字数を推定して `text_capacity` として利用すること
- 併せて `branding.json` 由来のフォント設定を廃止し、テンプレがブランドそのものになる前提へ移行すること

をまとめて進める計画です。 Plan にもこの前提を反映して提示します。

user
文字数推定について、プレースホルダー全体での文字数と、1行あたりの文字数 の2つを取得してね

assistant
Plan案（承認依頼）  
参照済み: `docs/policies/context-engineering.md`, `CONTRIBUTING.md`, `docs/policies/task-management.md`, `docs/roadmap/roadmap.md#rm-081`, `docs/requirements/stages/stage-03-compose.md`, `docs/design/schema/stage-03-mapping.md`, `docs/todo/20251124-rm081-text-capacity.md`

1. モデル整備と互換性方針  
   - `FontSpec`/`TextboxParagraph` をプレースホルダー抽出でも利用できるよう拡張し、`JobSpecScaffoldPlaceholder`・`SlideTextbox` に `font`（name/size/color/bold/italic）と段落設定（行間、左右インデント、段落前後余白）を保持する。  
   - `text_capacity` フィールドを `total_chars`/`chars_per_line`/`max_lines` などの構造で追加し、後方互換として既存データでは空値を許容。  
   - 影響: `src/pptx_generator/models.py`, `spec_loader.py`, `generate_ready.py`, `pipeline/renderer.py`, `pipeline/analyzer.py` ほか。

2. テンプレ抽出強化（タイトル等含む全テキスト枠）  
   - `TemplateExtractor` で PPTX の TextFrame からタイトル・サブタイトル・本文などテキスト型プレースホルダーすべてのフォント/段落情報を取得。Theme Font 指定時はテーマから実フォント名・サイズ・色を解決し、太字/斜体フラグも反映。  
   - プレースホルダー内部余白（左右/上下マージン）や段落インデントを読み取り、後段容量計算に渡す。  
   - 単体テスト（`tests/template_audit/test_template_extractor_jobspec_output.py` 等）で代表レイアウトの期待値を追加。

3. 文字数推定ユーティリティ  
   - `src/pptx_generator/utils/text_capacity.py`（新規）に、テキストボックス寸法・フォントサイズ・段落設定（行間、インデント、段落前後余白）を考慮して `max_lines`, `chars_per_line`, `total_chars` を算出する共通関数を実装。  
   - 箇条書き（bullet）が挿入される場合のレベル別インデント減算、太字やフォント係数による幅補正、フォント情報欠落時のフォールバックを定義。  
   - ユニットテストでケース（タイトル枠、本文枠、bullet インデントあり）を網羅。

4. text_capacity 埋め込みと活用  
   - `TemplateExtractor` で各テキスト系プレースホルダーに `text_capacity` を計算して格納。タイトル・本文すべて対象。  
   - `layout_validation` でも同ユーティリティを使用し、既存 `text_hint` を `text_capacity` 由来の値で整合させ、JSON レコードへ `text_capacity` を追加。  
   - `spec_loader`/`generate_ready` で `text_capacity` を SlideTextbox へ伝播し、Renderer・Analyzer が参照できるようにする。

5. ブランド設定依存の撤廃  
   - `branding.json` からフォント情報を参照しているコードパス（CLI 設定、Renderer、Analyzer、Refiner 等）を削除し、テンプレ抽出由来フォントをデフォルトとする。  
   - ブランド差し替えオプションを CLI から廃止し、関連ドキュメント（README/requirements/design/policies）と設定ファイルから該当項目を削除。  
   - 互換性維持のため、フォント情報のない古い JobSpec を読み込む際はテーマ既定値を推定して補完するフォールバックを実装。

6. ドキュメント/テスト更新  
   - `docs/design/schema/stage-03-mapping.md` などスキーマ資料・RM-081ロードマップ・ToDo メモを更新し、新しい `font`/`text_capacity` の仕様と利用箇所を明記。  
   - `samples/` 配下 JSON、`tests/integration/test_cli_generate_pipeline_flow.py` 等を新仕様に合わせて修正。  
   - ロールバック手順（テンプレ抽出結果の旧仕様へ戻す場合の対応）を ToDo に記載。

テスト計画:  
- `uv run --extra dev pytest tests/template_audit/test_template_extractor_jobspec_output.py`  
- `uv run --extra dev pytest tests/layout_validation`  
- 主要レンダリング/パイプラインテスト（例: `tests/pipeline/render/test_renderer_rich_content.py`, `tests/integration/test_cli_generate_pipeline_flow.py`）で回帰確認。

ロールバック:  
- 関連コミットを `git revert` し、ToDo へ理由を記録。既存 `branding.json` フォント設定を再参照するコードパスを復元すれば旧挙動に戻せる。

user
ありがとう。追加で以下を教えて。
1. プレースホルダーには、タイトルのボックスなども含まれますか？
2. 取得する情報はフォント名/サイズ/色だけで良いですか？太字かとかも取ったほうが良いのでは
3. bulletで挿入や、プレースホルダーで規定されている余白の情報は加味しなくて良いか

assistant
1. はい、テンプレ抽出で扱うプレースホルダーにはタイトル／サブタイトル／本文などテキスト枠全般が含まれます。`placeholder_type` が `TITLE`/`SUBTITLE`/`BODY` 等であっても同じ仕組みでフォント・文字数目安を付与します。

2. 文字数推定や後段レンダリングを正しく行うには、フォント名・サイズ・色に加えて太字 (`bold`)、斜体 (`italic`)、行間・インデント等の段落情報も取得しておく方が望ましいです。特に太字や行間は実際に占有する幅／高さに影響するため、箇条書きや本文の容量推定精度にも寄与します。従来の `FontSpec` に `bold`/`italic` は既にありますが、テンプレ抽出でそれらを埋めるようにします。

3. 余白（左右インデント・段落前後のスペース）やプレースホルダー内部のマージンは実質的に表示可能領域を減らすので、容量推定に反映すべきです。既存 `_derive_text_hint` は単純な幅×係数で見積っていましたが、仕様変更後はテンプレから取得した段落設定（左/右インデント、`space_before/after`, `line_spacing`）を考慮し、実際のテキスト領域や行間を基に `max_lines`・`chars_per_line` を算出する方針で進めます。

user
ありがとう、ではplanを見直して再提示して。

assistant
Plan（承認依頼）  
参照済み: `docs/policies/context-engineering.md`, `CONTRIBUTING.md`, `docs/policies/task-management.md`, `docs/roadmap/roadmap.md#rm-081`, `docs/requirements/stages/stage-03-compose.md`, `docs/design/schema/stage-03-mapping.md`, `docs/todo/20251124-rm081-text-capacity.md`

1. モデル整備と互換性方針  
   - `FontSpec`/`TextboxParagraph` をプレースホルダー抽出でも利用できるよう拡張し、`JobSpecScaffoldPlaceholder`・`SlideTextbox` に `font`（name/size/color/bold/italic）と段落設定（行間、左右インデント、段落前後余白）を保持する。  
   - `text_capacity` フィールドを `total_chars`/`chars_per_line`/`max_lines` などの構造で追加し、後方互換として既存データでは空値を許容。  
   - 影響: `src/pptx_generator/models.py`, `spec_loader.py`, `generate_ready.py`, `pipeline/renderer.py`, `pipeline/analyzer.py` ほか。

2. テンプレ抽出強化（タイトル等含む全テキスト枠）  
   - `TemplateExtractor` で PPTX の TextFrame からタイトル・サブタイトル・本文などテキスト型プレースホルダーすべてのフォント/段落情報を取得。Theme Font 指定時はテーマから実フォント名・サイズ・色を解決し、太字/斜体フラグも反映。  
   - プレースホルダー内部余白（左右/上下マージン）や段落インデントを読み取り、後段容量計算に渡す。  
   - 単体テスト（`tests/template_audit/test_template_extractor_jobspec_output.py` 等）で代表レイアウトの期待値を追加。

3. 文字数推定ユーティリティ  
   - `src/pptx_generator/utils/text_capacity.py`（新規）に、テキストボックス寸法・フォントサイズ・段落設定（行間、インデント、段落前後余白）を考慮して `max_lines`, `chars_per_line`, `total_chars` を算出する共通関数を実装。  
   - 箇条書き（bullet）が挿入される場合のレベル別インデント減算、太字やフォント係数による幅補正、フォント情報欠落時のフォールバックを定義。  
   - ユニットテストでケース（タイトル枠、本文枠、bullet インデントあり）を網羅。

4. text_capacity 埋め込みと活用  
   - `TemplateExtractor` で各テキスト系プレースホルダーに `text_capacity` を計算して格納。タイトル・本文すべて対象。  
   - `layout_validation` でも同ユーティリティを使用し、既存 `text_hint` を `text_capacity` 由来の値で整合させ、JSON レコードへ `text_capacity` を追加。  
   - `spec_loader`/`generate_ready` で `text_capacity` を SlideTextbox へ伝播し、Renderer・Analyzer が参照できるようにする。

5. ブランド設定依存の撤廃  
   - `branding.json` からフォント情報を参照しているコードパス（CLI 設定、Renderer、Analyzer、Refiner 等）を削除し、テンプレ抽出由来フォントをデフォルトとする。  
   - ブランド差し替えオプションを CLI から廃止し、関連ドキュメント（README/requirements/design/policies）と設定ファイルから該当項目を削除。  
   - 互換性維持のため、フォント情報のない古い JobSpec を読み込む際はテーマ既定値を推定して補完するフォールバックを実装。

6. ドキュメント/テスト更新  
   - `docs/design/schema/stage-03-mapping.md` などスキーマ資料・RM-081ロードマップ・ToDo メモを更新し、新しい `font`/`text_capacity` の仕様と利用箇所を明記。  
   - `samples/` 配下 JSON、`tests/integration/test_cli_generate_pipeline_flow.py` 等を新仕様に合わせて修正。  
   - ロールバック手順（テンプレ抽出結果の旧仕様へ戻す場合の対応）を ToDo に記載。

テスト計画:  
- `uv run --extra dev pytest tests/template_audit/test_template_extractor_jobspec_output.py`  
- `uv run --extra dev pytest tests/layout_validation`  
- 主要レンダリング/パイプラインテスト（例: `tests/pipeline/render/test_renderer_rich_content.py`, `tests/integration/test_cli_generate_pipeline_flow.py`）で回帰確認。

ロールバック:  
- 関連コミットを `git revert` し、ToDo へ理由を記録。既存 `branding.json` フォント設定を再参照するコードパスを復元すれば旧挙動に戻せる。

user
承認します。この内容をtodoに書いてね。
また、ここまでのディスカッションをnoteに要約せず全文そのまま転記してほしい。
