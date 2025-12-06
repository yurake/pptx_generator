# RM-086 静的テンプレ外部フック統合 会話ログ

ユーザー:
- static modeのみでの実行を想定しています
- 今後このような、「特有のテンプレート」と「特有のinput」からstatic modeでの反映を行うパターンは増える見込み。その度にマージを考えるのが大変なため、大枠の4stageでコマンドはそのまま、stageごとに外部スクリプトが用意されていればそれを呼び出して処理は委譲し、in/outの整合だけ取れる仕組みを入れるのはどうかな？

アシスタント:
静的専用テンプレ＋入力の取り込み方針  
- static mode 前提なら既存 CLI (`template`→`prepare`→`compose`→`generate`) は維持し、各 stage が “外部スクリプトあり/なし” を判定して I/O だけ統一するのが有効。CLI が `stage_n` ディレクトリに置かれたファイルを期待しているため、スクリプトはその契約に従って入出力を担う。

- **Stage 1: テンプレ整備 (docs/design/stages/stage-01-template.md 参照)**
  - `経費投資テンプレ.pptx` を `uv run pptx template` で抽出し、`template_spec.json`・`jobspec.json` にメッセージライン用テキストプレースホルダー／表アンカーを登録。
  - 既存テンプレにない命名規則は `config/usage_tags.json` と整合させる。必要なら `layouts.jsonl` へテーブル構造の列見出しやアンカー名を追記。
  - mapping_config 相当のルールはテンプレメタに移し、列→アンカーの突合ルールを Stage 3 が参照できる形（例: `jobspec` の `table_mapping` 拡張）で管理する。

- **Stage 2: コンテンツ準備 (src/pptx_generator/prepare)**
  - 新しいソースアダプタを追加し、Excel を `PrepareSourceDocument` へ変換する。`openpyxl` で抽出しつつ `億円` 換算や「◯年」正規化をここで実施。
  - メッセージラインはレコメンドすべき章 (intent) と紐付け、表データは `ContentSlide.elements.table_data` に載せられるよう `PrepareSourceChapter` → `DraftSlideCard` へ流す。
  - 変換ルールは `prepare` 側で Pydantic モデル化し、JSON 保存 (`prepare_card.json`) に残るようにする。CLI には `uv run pptx prepare --input excel --mapping config/...` のような引数拡張を検討。

- **Stage 3: マッピング (src/pptx_generator/pipeline/mapping)**
  - Excel 由来のカードにテーブル payload を付与し、`MappingSlideProcessor._build_table_payload` が扱える形で `content_slide.elements.table_data` を構築。
  - メッセージラインは専用レイアウト（例: 表紙／サマリー）へ割付するルールを `MappingWorkItem` 生成時に追加し、`usage_tag` や `layout_candidates` を活用して適切なレイアウトへ誘導。
  - mapping_config の「target」情報は `jobspec` / `rules.json` 側に移し、`table_anchor.resolve_table_anchor` で列・セル位置を特定する。マッチ失敗時は `MappingFallbackState` に記録してフォールバックの可視化を維持。
  - ログ (`draft_mapping_log.json`) で換算後の値を追跡できるよう `MappingLogSlide` へ formatted 値を残す。

- **Stage 4: レンダリング (src/pptx_generator/pipeline/renderer)**
  - 既存レンダラで表データを描画できるか確認し、不足があれば `render_table` 系ハンドラを拡張して `formatted_value` を配置、単位は `generate_ready.meta` で補う。
  - メッセージラインはテキスト要素として流し込み、禁則制御やフォント設定はテンプレスタイル (`generate_ready_meta.template_style`) に任せる。
  - 直接 `Presentation` を開く処理は不要になるため、`temp/excel_mapper.py` の `_apply_message_line`／`_apply_table_data` ロジックはステージ 3→4 の責務分割後に削除。

- **追加検討事項**
  - 設定ファイル: 旧 mapping_config.json は `config/` かテンプレ配下へ移動し、Pydantic モデルでスキーマ化。円→億円換算レートは `settings` に環境変数対応で収める。
  - CLI フロー: `uv run pptx generate` の stage 実行順に Excel 取り込みオプションを追加し、HITL 操作のために `docs/todo/` で ToDo を起票する。

- **リスク / 課題**
  - Excel のセル番地依存が強いためテンプレ変更に弱い。`jobspec` 側へ列名マッピングを移し、セル番地ではなくアンカー＋オフセットで表現する必要がある。
  - 換算ロジックの丸め誤差や N/A 処理をステージ 2 で確定させないと、後続ステージとの整合性が崩れる。Pydantic でバリデーションを入れる。
  - テーブル構造が複雑な場合、現状の `MappingSlideProcessor` が特定列決め打ちで動くため、レイアウト別ルールを拡張または新しい Table ハンドラが必要。

- **検証方針**
  - Stage 2: Excel 入力→`prepare_card.json` のユニットテスト（`pytest`）で換算値・エラーハンドリングを確認。
  - Stage 3: `tests/integration` に Excel→`generate_ready.json` のモックパイプラインテストを追加し、候補レイアウト選択とフォールバックログを検証。
  - Stage 4: `uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py` を Excel シナリオで拡張し、生成された PPTX の該当スライドを `python-pptx` で検証。
  - CLI: `uv run pptx prepare`／`uv run pptx generate` シナリオを ToDo に記録し、HITL 操作ログが `draft_mapping_log.json` に残ることを確認。

- **次のアクション候補**
  1. Excel→Prepare 変換モジュールのインターフェース設計（入力シグネチャ／設定）を決定。
  2. テンプレ抽出を実行し、必要なアンカー名・レイアウトメタを `jobspec` に反映。
  3. Stage 3 のテーブルマッピング要件を整理し、`table_anchor` 拡張のスコープを見積もる。

ユーザー:
- 構造案
   - template実行時に .pptx/slide_inputs.md や .pptx/extract/prompts を用意している認識。ここを拡張するのはどうかな
   - それとも external/におけるようにした方が良い？ .pptxは一時領域で、external/はリポジトリへコミットはされないが消されない領域の認識

アシスタント:
- `.pptx/slide_inputs.md` や `.pptx/extract/prompts` はテンプレ抽出結果／レビュー用メモで、`uv run pptx template --clean` 等で再生成・削除される前提です。ここに stage フックを置くと「テンプレ差し替えのたびに消える」「CI で掃除される」ため、恒久的な外部スクリプト置き場には向きません。参照パスとしては使えても、実行スクリプト本体を保管する領域には避けたいです。
- 一方 `external/` は git 管理外でローカルに残り続けるため、静的テンプレ固有のフックを置く場所としては自然です。テンプレごとに `external/static_hooks/<template_id>/stage02_prepare.py` のように分けておけば、リポジトリに混ぜずに済み、複数テンプレの共存・切替もスクリプト差し替えだけで行えます。CI や他環境への配布が必要なら zip/Tar で配布して展開してもらう運用にできます。
- 推奨構成は以下です。  
  - フック設定はリポジトリ管理 (`config/pipeline_hooks.yaml` 等) に置き、テンプレ ID → Stage → 実行スクリプトパス（`external/…` 相対）を記録。  
  - CLI は template stage でテンプレ ID を確定後、対応するフックを `external/...` から呼び出す。`.pptx/` 配下には従来どおり成果物（`slide_inputs.md` や抽出結果）だけ生成。  
  - テンプレごとに `.pptx/` へ Hook 実行結果（例えば `generate_ready.json` の検証ログ）を書き戻すのは OK だが、スクリプトそのものは `external/` に保持する。
- もしテンプレごとに配布資料をまとめたい場合は、`.pptx` を「成果物一時領域」、`external/` を「テンプレ固有ロジックの保管庫」と役割分担し、`template` stage で必要に応じ `.pptx/slide_inputs.md` や `.pptx/extract/prompts` へ参照パスを書き込む形にすると整理しやすいです。

ユーザー:
- フック設定はgit管理外のexternalに依存するので、externalに配置したい、git管理したくない

アシスタント:
了解しました。`external/` をフックと設定の唯一のソースにし、リポジトリ側はそれを探して実行する枠組みに寄せると良さそうです。以下のイメージでどうでしょうか。

- **構成方針**
  - `external/` 以下にテンプレート ID ごとのディレクトリを作り、そこへステージフックと設定ファイル（例: `stage02_prepare.py` と `hooks.yaml`）を配置。
  - リポジトリ側の CLI は「現在のテンプレ ID」を判別したうえで `external/<template_id>/hooks.yaml` を読み込み、各 stage の実行ファイルを決定。設定が見つからない場合は従来ロジックにフォールバック。
  - `hooks.yaml` にはステージ番号 → 実行スクリプト相対パス、入出力ディレクトリなどを記述。例:
    ```yaml
    stage1: null
    stage2:
      cmd: ./stage02_prepare.py
      args:
        - "--input"
        - "../temp/投資経費一覧dummy.xlsx"
    stage3: ./stage03_compose.py
    stage4: null
    ```
  - CLI 実行時に `external/` が未配置なら警告しつつデフォルト処理を継続。CI や共有環境では `external/` を事前に配布するだけで運用可能。

- **実装ポイント**
  - Stage 起動前に `external/<template_id>/hooks.yaml` を探す仕組みを CLI に追加。テンプレ ID 判定は `jobspec.json` など既存メタを利用。
  - フックは標準入出力かファイルパス引数で通信する。CLI 側は stage ディレクトリを引数で渡し、フックが必要な成果物（`prepare_card.json` など）を書き出す。
  - エラーハンドリングは終了コード／標準出力の JSON 等で判定し、失敗時はログへ記録して停止。成功時は既存パイプラインが次の stage をそのまま処理できる。

- **運用**
  - `external/` は git 管理外のままローカルに保持。テンプレ入れ替え時は外部ディレクトリの内容も更新するだけで、リポジトリへのマージ不要。
  - `.pptx/` は従来どおりテンプレ抽出・成果物保存の一時領域として使用し、フックスクリプトの参照を差し込む場合のみ（例: `slide_inputs.md` に「外部スクリプト: ../external/...」リンクを書き込む）とする。

ユーザー:
- static modeにおいて、stage 1とstage 3で異なる処理をしたい場合ってあるかな？
- 加えて、slideごとにも指定できるといい

アシスタント:
**Stage 1 / Stage 3 の役割分担**  
- static mode でも Stage 1（テンプレ抽出）と Stage 3（マッピング）は性質が異なります。  
  - Stage 1 はテンプレ側の構造・アンカー・メタデータを登録する工程。外部スクリプトで「テンプレ依存の部品を追加抽出する」「テンプレ固有の補助ファイルを生成する」ニーズが出ます。  
  - Stage 3 は入力（prepare成果物）をレイアウトへ割り当てる工程。たとえばテンプレ固有の優先順位ルールや差分レイアウトを採用するなど、Stage 1 とは別軸のロジックが必要になる場面があります。  
- static mode でもテンプレ入替・部分更新時に「抽出ロジックは標準、そのまま使う」「マッピングだけ差し替える」といったケースがあり得るため、Stage 1 と Stage 3 を別々にフックできる余地は残しておく方が柔軟です。

**スライド単位での指定**  
- テンプレ／入力の組み合わせによってスライドごとに固有処理が必要な場合、フック設定で slide ID/レイアウト ID をキーにして分岐できるのが望ましいです。  
  - `hooks.yaml` に `slides:` セクションを追加し、`stage` ごとに `slide_id` → ハンドラを登録（例: `slide_01_cover` は Stage 3 の特別な割り当てロジックを実行）。  
  - Stage 2/3 のフックスクリプト内では、CLI から渡された `generate_ready` などのメタにアクセスしてスライド ID ごとに処理を切り替える。  
  - Stage 4 側で別 renderer を使う必要がある場合も、同じ仕組みで `slides.<slide_id>.stage4` に外部スクリプトを指定して差し替える。

**次のアクション案**  
1. `hooks.yaml` の拡張仕様（Stage 別・Slide 別のキー構造、引数の受け渡し）を設計。  
2. CLI に Stage/Fallback の解決順序（テンプレ全体 → スライド個別）を実装。  
3. Excel マッピングのパイロットで、Stage 3 のスライド別ハンドラと Stage 4 の特化処理を試作し、テストパターンを整える。

ユーザー:
- jsonかmdファイルをこのプロジェクトでは使ってきているが、yamlが良い？

アシスタント:
このリポジトリでは `jobspec.json` や `generate_ready.json` など JSON／Markdown を既存契約として使っているので、フック設定も JSON（あるいは Markdown 内のコードフェンス）で揃える方が自然です。YAML にすると表現力は上がりますが、以下の点で差が出ます。

- **既存との一貫性**: CLI や `SpecLoader` は JSON 前提のパーサが多く、設定だけ YAML にすると読み込み系を増やす必要があります。
- **CI／検証**: 既存の JSON Schema や Pydantic モデルを流用できるのは JSON の利点。YAML 用に新たなバリデータを整備する手間が増えます。
- **テンプレ固有の柔軟性**: もしハンドラをスライド単位で細かく指定したい場合も、JSON でネストを表現できます。例:
  ```json
  {
    "stage2": {"cmd": "./stage02_prepare.py"},
    "slides": {
      "slide_01_cover": {"stage3": "./handlers/cover_mapping.py"}
    }
  }
  ```

Markdown（ToDo やメモ）にハンドラ設定を書いても CLI から扱いづらいので、フック設定は JSON で固定し、コメントや補足は `external/.../README.md` に分けるのが運用しやすいと思います。

ユーザー:
ok, rmやtodoがないと思うので、開発の準備を進めよう。
rmが採番されたらtodoを作成する前に、ここまでのディスカッションの内容を正確に漏らさずnotesに転記して記録を残して。

アシスタント:
了解しました。RM が採番されたら、ToDo を起票する前に本スレッドで整理した方針・構成案を漏れなく `docs/notes/` 配下へ転記します。その後、指定された手順どおり ToDo／ブランチ準備へ進みますので、RM 連絡をお待ちしています。

ユーザー:
rmの採番もやって

アシスタント:
静的テンプレ外部フック統合のテーマを RM として登録し、ここまでの検討内容をノートに残しました。  

- `docs/roadmap/roadmap.md:59` に Stage 3 のメルマイドへ `RM-086 静的テンプレ外部フック統合` を追加。  
- `docs/roadmap/roadmap.md:1085` 以降に RM-086 の詳細（対象ステージ、依存、期待成果、次アクション）を新設。  
- `docs/notes/20251204-rm086-static-hooks.md:1` に今回の議論（静的モード適用範囲、external/ でのフック管理、スライド別指定、JSON 設定方針、想定タスク）を漏れなく整理。

次のステップ案:
1. RM-086 に紐付く ToDo を作成し、ブランチ準備と Plan 承認フローへ進む。
2. フック設定フォーマットと CLI 側の探索ロジック草案を起こし、Excel マッピング案件での試作計画を立てる。

ユーザー:
 notesについて、漏れなくというのは整理要約せず、1語1句同じ内容を転記してという意味なんだけど。

## 2025-12-06 作業ログ
- `external/経費投資/mapping_config.json` に Excel セル番地と `target` 名称を追加し、初期計／期間請負／社員／内製開発／PJ 管理／PN／SI／ランニング計の提示額・利益を網羅。
- `external/経費投資/stage04_gen.py` で `TABLE_CELL_MAPPINGS` を正規化キーへ更新し、`runtime/context.json` の `extract_summary.table` から表セルへ値を差し込む処理を追加。
- 静的パイプライン (`template`→`prepare`→`mapping`→`gen`) を再実行し、`docs/runbooks/release.md` に記載した Python スニペットで `.pptx/jri/gen/jri_static_output.pptx` の表セルと `context.json` の `extract_summary.table` が一致することを確認。
- ドキュメント（`docs/roadmap/roadmap.md`, `docs/requirements/requirements.md`, `docs/runbooks/release.md`, `docs/runbooks/runbooks.md`, `README.md`, `AGENTS.md`）を更新し、外部フック運用とテーブルマッピング手順を追記。
- 静的出力レビュー用に `scripts/inspect_static_pptx.py` を追加し、テンプレートと生成結果のテキスト・表セル差分を CLI で確認できるようにした。
- Stage4 フックを更新し、`templates/経費投資.pptx` のレイアウトを複製して静的文言を保持しつつ、メッセージライン・表セルを正しく差し込めるようにした。
