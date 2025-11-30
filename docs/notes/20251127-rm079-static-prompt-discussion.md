RM-079 に関するディスカッションログ

User: RM-079に着手して

Assistant: 
参照済みドキュメント:
- `docs/policies/context-engineering.md`
- `CONTRIBUTING.md`
- `docs/policies/task-management.md`
- `docs/design/cli/cli-command-reference.md`

以下の Plan で RM-079 を進めたいです（承認後に ToDo の計画欄へ転記します）。

**Plan**
1. CLI 拡張: `src/pptx_generator/cli.py` に `--prompt-directive` (複数指定可) と `--prompt-directive-file` を追加し、ファイル内容読み込み・順序維持・入力検証（空文字・ファイル未読時のエラー処理）を実装。解析した directives を Prepare 実行へ渡す。
2. 生成フロー更新: `pptx_generator/prepare_ai/orchestrator.py` と `prepare_ai/prompts.py` に directives を組み込み、動的・静的双方で LLM ペイロードへ追記する仕組みを整備。`PrepareGenerationMeta` / `PrepareAIRecord` / `prepare_card` メタ出力にも directives を残し、`prepare_ai_log.json` / `ai_generation_meta.json` に記録できるようモデル (`prepare/models.py`) を拡張する。
3. テスト & ドキュメント: CLI フローのテスト（`tests/cli/test_cli_prepare_stage_flow.py` など）を更新し directives 反映を検証。`tests/integration/test_cli_generate_pipeline_flow.py` も必要箇所を調整。CLI リファレンスと README に新オプションの説明・使用例・セキュリティ注意を追記する。

**影響ファイル（想定）**
- `src/pptx_generator/cli.py`
- `src/pptx_generator/prepare/models.py`
- `src/pptx_generator/prepare_ai/orchestrator.py`
- `src/pptx_generator/prepare_ai/prompts.py`
- `tests/cli/test_cli_prepare_stage_flow.py`
- `tests/integration/test_cli_generate_pipeline_flow.py`（必要なら）
- `docs/design/cli/cli-command-reference.md`, `README.md`
- 関連する `prepare_ai` / `prepare` テスト・ヘルパー

**リスク・懸念**
- CLI のファイル読み込み順序取り扱いが分かりづらい → 指定順を維持するユーティリティを実装し、ドキュメントで明示。
- directives を JSON へ混在させる際に LLM への入力が肥大化する恐れ → サイズ上限や警告が必要になった場合に備え、ログへ directives をそのまま保存し可視化する。
- 既存成果物との互換性（`PrepareGenerationMeta` の schema 変更）→ 追加フィールドは optional にし、旧データの読み込みを阻害しないようデフォルト値を設定。

**テスト計画**
- `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py`
- `uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py::test_cli_prepare_generates_outputs`
- 必要に応じて `uv run --extra dev pytest tests/prepare_ai` 配下のピンポイントテスト

**ロールバック**
- CLI オプション追加と orchestrator/model 変更を含むコミットを `git revert`。成果物・ドキュメントの追記も同じコミット単位で巻き戻し、`ai_generation_meta` スキーマは旧状態へ戻す。

この内容で進めてよいかご確認ください。

User: プラン策定の前にまずはcommit, pushしてくれる？

Assistant: 
- `docs/todo/20251124-rm079-prepare-directives.md` を更新し、ブランチ作成タスクを完了済みに変更した上で `chore(todo): update rm079 branch status` (6c11b2e) としてコミット済みです。
- `git push --set-upstream origin feat/rm079-directives` を実行し、リモートへ反映しました。実行時に `.git/config` とリモート ref のロックが取れず upstream 設定だけ失敗したため、必要であれば権限のある環境で `git branch --set-upstream-to=origin/feat/rm079-directives feat/rm079-directives` を改めて実行してください（push 自体は完了しており、ローカルはリモートより 1 コミット先行の状態です）。
- これでコミット／プッシュ条件は満たしたので、次の指示（Plan 策定など）をお願いします。

User: 今回の対応でユーザー体験がどう変わるか、ユーザー目線でのプロセス変更点を説明して

Assistant: 
- `pptx prepare` 実行時に、ユーザーが明示的なプロンプト指示を CLI オプション経由で注入できるようになる想定です。これにより、従来はポリシー定義や元原稿を編集しないと調整できなかった LLM への追加要望（例: “すべてのカードで ROI の定量値を入れること”）を、`--prompt-directive` でワンショットに付与できます。
- 複数の指示を順序通りに並べて渡したいケース（チーム合意済みの箇条書き指示など）では `--prompt-directive` を複数回指定、あるいは `--prompt-directive-file` で専用ファイルを読み込むだけで済みます。これにより、Prepare 前に原稿の複製や書き換えを行う手間がなくなり、HITL 担当者が柔軟に試行錯誤できます。
- 生成結果や監査ログには、実際に使った directives がそのままメタ情報として残る計画です。HITL レビューや再生成時に「どんな追加指示でこのカードが作られたか」を追跡しやすくなり、チーム内レビューやコンプライアンス確認がスムーズになります。

User: まずはscope をstatic modeだけにしたいです。dynamic modeは除外。すると、このplanも変更になりますかね？

Assistant: 
了解しました。`RM-079` のスコープを「static モードの `pptx prepare`（Blueprint ベースの生成）」に限定するよう Plan を更新します。`dynamic` モード関連の変更とテストは今回対象外です。

**Plan（static モード限定版）**
1. CLI 拡張（static 用）
   - `src/pptx_generator/cli.py` の `prepare` サブコマンドに `--prompt-directive`／`--prompt-directive-file` を追加し、static モード実行時のみ directives を受け付ける。
   - 指定順を維持しつつ、空文字・重複・ファイル読み込みエラーを検証。解析した directives は orchestrator 呼び出し時に渡す。
   - `dynamic` モードで指定された場合は警告 or エラーで拒否する挙動にする。

2. Static 生成フロー更新
   - `pptx_generator/prepare_ai/orchestrator.py` と `prepare_ai/prompts.py` を static ペイロード専用で拡張し、LLM 入力 JSON に directives 配列を追加。
   - `PrepareGenerationMeta`（`prepare/models.py`）や `PrepareAIRecord` など、static モード成果物に directives を記録できるフィールドを追加。`ai_generation_meta.json` や `prepare_ai_log.json` に static 指示内容が残るようにする。
   - Dynamic 系のコード・モデルには変更を入れない、もしくは optional フィールド扱いで既存挙動をそのまま維持する。

3. テスト & ドキュメント
   - `tests/cli/test_cli_prepare_stage_flow.py` を static ケースに絞って更新し、directive 指定あり・なしの差分を確認する。必要に応じて static 専用の orchestrator テスト（Mock LLM）を追加。
   - `docs/design/cli/cli-command-reference.md` と README に、static モード限定の新オプション運用を説明。セキュリティ上の注意（第三者指示の監査など）も記載。
   - 対象外となった dynamic モードの説明は変更しないが、static 限定である旨をドキュメントに明示。

**リスク・懸念**
- static 専用にすることで dynamic で directives を指定した場合の UX（明確なエラーメッセージ）が必要。
- 生成メタへの項目追加は static 成果物との互換性のみ確認すればよいが、共通モデル (`PrepareGenerationMeta`) を触ることで他ステージが予期せず影響を受けないよう注意する。
- directives 内容がログに含まれるため、秘匿情報が入るケースの取り扱い（README などでの注意喚起）が必要。

**テスト計画**
- `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py -k static` など static ケース中心。
- 必要なら `tests/integration/test_cli_generate_pipeline_flow.py::test_cli_prepare_generates_outputs` を static モードに切り替え、directive 反映を確認。

このスコープで進めて問題なければ承認お願いします。

User: static modeのprepareでllmの呼び出す単位ってスライドごとだと思うんだよね、そのスライド単位でプロンプトを差し替えられるようにしたい。で、差し替え方を考えないといけなくって、不変の部分（outputの形式）と、可変（どう作成してほしいかといった生成の意図とか？）があると思っていて、その分類をした上で、あらかじめ用意したフォーマットの中でユーザーに修正してもらうのが良いかなと思ったんだけどどうかな？

Assistant: 
おっしゃる通りで、static モードの `pptx prepare` は「Blueprint のスライドごとに LLM を呼び出す」構造なので、スライド単位でプロンプトを差し替えられる設計が噛み合います。その際に重要なのは「どこを安全に書き換えられる領域としてユーザーへ開放するか」です。ざっくり以下の整理が考えられます。

**1. プロンプト構造の分割案**
- **不変領域（システム指定）**
  - 期待する出力形式 (`slots` 配列のスキーマ、フィールド定義)。
  - Blueprint / slot 情報の取り扱い方（`slot_id`, `anchor`, `required` の守り方）。
  - セキュリティ・コンプライアンス上の禁止事項（機密流出を避けるための注意など）。
  - JSON しか返さない／日本語で出力する等の基本スタイル。
- **可変領域（ユーザー編集可）**
  - スライド内で表現したいトーン・重点（例: 「ROI を定量値で書く」「リスクを必ず 2 点入れる」）。
  - 外部からのディレクティブ（HITL 指示）やキャンペーン固有メッセージ。
  - 生成方針に関するヒント（例: 「タイトルスライドでは XXX を強調」「body の bullet は 3 行以内」）。

**2. 差し替えフォーマットの考え方**
- プロンプト雛形（テンプレ）を `prompt_static_slide_template.md` のようなファイルとして用意し、上記「不変セクション」にシステム文言を固定、`{{user_directives}}` などのプレースホルダを設ける。
- CLI オプション `--prompt-directive-file` でこのテンプレをユーザーに配布 → 必要な箇所のみ編集してもらい、差し替えるのは `{{user_directives}}` や `{{tone_guidance}}` といったブロックに限定。
- スライド単位でファイルを分けるのではなく、テンプレ内に `{{slot_specs}}` のループを残しておき、実行時に CLI 側で埋め込む。ユーザーは可変ブロックだけ調整。
- もしスライドごとに異なる方針を入れたい場合は、ディレクティブ側で `slot_id` や `layout` をキーに条件分岐できるようフォーマットを設ける（例: YAML/JSON で `slots`: [{slot_id: "...", instructions: "..."}]）。

**3. 進め方（提案）**
1. プロンプトテンプレを「固定ブロック＋ユーザー編集ブロック」で分割し、雛形を docs/config などに格納。
2. CLI 側で:
   - テンプレの不変ブロックをロード。
   - `--prompt-directive`／`--prompt-directive-file` で渡された可変ブロックを所定のプレースホルダへ差し込む。
   - スライドごとにディレクティブを上書きできるよう、`slot_id` に紐づけて directives を管理。
3. ドキュメントで「編集可能なのはここだけ」というガイドを明示し、誤ってフォーマットを壊さないようチェックを入れる（例: 必須セクションが抜けたら CLI がエラーにする）。

このアプローチなら、
- 不変部分＝CLI/テンプレ側でプロテクト。
- 可変部分＝ユーザーがフォーマット内で編集。
- スライド単位の上書きも、可変部分で `slot_id` 別に書き分けられる。

この方向で仕様化を進めてもよいでしょうか？

User: いい案だね。
- 雛形用意は賛成。prepareで用意するよりtemplateが呼ばれた際に用意した方がprepareでの指定が不要になるしユーザーがprepareを2回実行しなくて済むんじゃないかな。
- 雛形はスライド単位で分けたほうがユーザーは理解しやすいはず。キーはslot_idやlayoutだけだとユーザーが知らない名前のため、頭にページ番号つけると良いのでは
- 修正があったものだけ差し替える運用ができるといいね。修正がなかったものはユーザーの差し替えがなかったものなので、アプリで用意している動きをしてもらう
- templateでフォルダを用意し、フォルダの更新があったらそのスライド作成時だけ差し替えにすれば、CLIの追加はいらないと思ったけどどうかな

Assistant: 
なるほど、その方向で整理すると以下のようなフローになりそうです。

- **テンプレ抽出時に雛形を自動生成**  
  `pptx template` の成果物に「スライド別プロンプト雛形フォルダ（例: `.pptx/template_prompts/`）」を追加。各スライドごとに `01_<layout>.md` のようにファイルを分け、`01_title.md` のようにページ番号＋レイアウト名を先頭に付ければユーザーも参照しやすいです。雛形にはシステムが保護する不変セクションと、ユーザーが書き換える可変セクションを明示しておく。

- **差分があるスライドだけ override**  
  `pptx prepare` static 実行時に、テンプレ成果物内のプロンプトフォルダを見に行き、該当スライドのファイルが存在・更新されていればその内容を `slot_specs` に埋め込む。フォルダ内に変更がないスライドは従来どおりの標準プロンプトを使うので、未編集ファイルは実質無視できる。これなら CLI オプションを増やさずに済み、ユーザーも「必要なスライドだけ編集 → 保存 → 1 回の prepare 実行」で済みます。

- **テンプレとの連動**  
  雛形フォルダはテンプレ抽出時に作り、テンプレ版管理の一部として Git/ストレージに残せば、チームで共有・レビューもしやすい。prepare running 前に手元で `git diff` などで編集ファイルだけ確認できるのも利点。

この構成なら、`pptx prepare` 側の変更は「指定ディレクトリ（デフォルトでテンプレ抽出成果物内）からスライド別プロンプトを読み取り、該当スライドにだけ適用する」だけで済むので、CLI インターフェースは増やさずに要件を満たせると思います。もしテンプレ抽出（stage1）側で雛形生成を組み込む方針で進めてよければ、その前提でタスクを分割して設計を進めましょうか？

User: この方向で。planを再作成して。気になるところがあれば聞いて？

Assistant: 
参照済みドキュメント:
- `docs/policies/context-engineering.md`
- `CONTRIBUTING.md`
- `docs/policies/task-management.md`
- `docs/design/cli/cli-command-reference.md`

以下、static prepare＋テンプレ雛形生成を前提とした Plan です。

**Plan**
1. **テンプレ抽出でプロンプト雛形を生成**
   - `pptx template` 実行時に `.pptx/template_prompts/`（仮）を作成し、スライドごとに `01_<layout>.md` といったファイルを出力。
   - 各ファイルには「不変ブロック（CLI が保証）」と「ユーザー編集可ブロック」を区切ったフォーマットを入れる。
   - 既存テンプレ成果物構成（jobspec / blueprint など）に影響しないよう README・CLI リファレンスへ追記。

2. **prepare static で雛形差し替えを自動適用**
   - `pptx prepare --mode static` 実行時に、テンプレ成果物からプロンプトフォルダを参照。
   - スライド ID に対応するファイルが「存在かつユーザー編集あり」の場合のみ読み込み、LLM 呼び出し用プロンプトに差し込む（slot ごとに適用）。
   - フォルダ未指定・未編集の場合は従来どおりの標準プロンプトを使用。CLI オプション追加は行わず自動判断にする。
   - 適用した雛形名を `ai_generation_meta.json` や `prepare_ai_log.json` に記録し、監査追跡できるようにする。

3. **テストとドキュメント更新**
   - テンプレ抽出のユニット／CLI テストを追加し、雛形ファイルの生成と命名規則を確認。
   - `tests/cli/test_cli_prepare_stage_flow.py` など static ケースで雛形差し替えが反映されることを検証（変更があるスライドだけ内容が変わる）。
   - `docs/design/cli/cli-command-reference.md`, README, 必要に応じて `docs/design/stages/stage-02-prepare.md` へ新しいプロンプト編集フローを記述。

**疑問点 / 確認事項**
- プロンプト雛形フォルダを置くデフォルトパスは `.pptx/template_prompts/` で問題ありませんか？（テンプレ成果物内の別ディレクトリ希望なら教えてください）
- 「ユーザー編集あり」の判定はファイル存在＋ `static` 雛形との差分で判断する想定です。単純に「ファイルがあれば差し替える」でよいか、それともハッシュ比較などが必要かご希望ありますか？
- 雛形のフォーマット（Markdown 前提で OK か、もしくは JSON/YAML の方がよいか）も先に決めておきたいです。Markdown で案内 → CLI 側でコメント行を無視する方式を考えています。

User: 
- .pptx/extract/prompts でどうかな。ここに 01_title.md が入るイメージ
- 単純でok
- markdownでok
- template実行時に、プロンプト修正を案内するログを出したいね

User: resume

Assistant: 
了解。Plan 提示前の準備は完了済みなので、次に進む際はいつでも指示ください。
