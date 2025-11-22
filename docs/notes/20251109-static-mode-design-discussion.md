設計方針を擦り合わせたい。
私がイメージしているのは以下。現在の設計や実装との乖離がないかをチェックして。

静的テンプレートモード設計
ユーザーが準備したテンプレートのpptxはスライドの順番、プレースホルダー、ページ数が固定になっており、このテンプレートに合わせてコンテンツを配置する必要がある。
工程1 template では静的テンプレートであることをオプションで指定(例: --mode static)。outputはこれまでと同じjobspec.jsonやlayouts.jsonのままでok。
工程2 prepare では --mode static を指定。入力引数にjobspec.jsonを追加し、このjobspec.jsonに従ってスライド素材を生成する。出力は generate_ready.json で、動的テンプレートモードと同じスキーマを使う。ただし各スライド素材には jobspec.json の slide_id を紐付ける。outputはこれまでと同じprepare_card.jsonのままでok。**jobspecのcard1つ1つに対して適切なコンテンツを入力データから差し込む必要があり、これを生成AI呼び出しで行う。1ページずつ呼び出し**
工程3 compose では --mode static を指定。generate_ready.json と jobspec.json を参照し、outputはこれまでと同じdraft_approved.json、generate_ready.jsonのままでok。各json作成時には生成AI呼び出しを行う必要がないため、行わないように制御する。
工程4 変更なし

動的テンプレートモード設計
ユーザーが準備したテンプレートのpptxはスライドの順番やページ数は可変で、コンテンツに応じて適切なスライドを採用する必要がある。
コンテンツをスライド形式でドラフトしたのち（prepare_card.json）、テンプレートとマッピングして最終的なスライドを決定する（draft_approved.json、generate_ready.json）。
工程1 template では動的テンプレートであることをオプションで指定(例: --mode dynamic)。outputはこれまでと同じjobspec.jsonやlayouts.jsonのままでok。
工程2 prepare では --mode dynamic を指定。入力引数にjobspec.jsonは不要。出力はこれまでと同じprepare_card.jsonのままでok。**コンテンツをスライド形式でドラフトするために生成AI呼び出しを行う。全体で1回の呼び出し**
工程3 compose では --mode dynamic を指定。処理の内容（生成AIを2回呼び出す等）や、outputはこれまでと同じ。
工程4 変更なし

以下、いただいた設計イメージと現行実装のつながり／差分を整理しました。

**共通事項**
- `--mode dynamic/static` オプション導入・テンプレ種類の明示指定：実装済み。
- 動的モードの既存パイプライン構成は維持（工程4も変更なし）。

**工程1 template**
- 現行実装では `--layout-mode static` 指定時に `template_spec.json` へ `layout_mode` と Blueprint を自動追加します。
- いただいたイメージでは Stage1 の出力（jobspec/layouts）は既存通りを想定とのことですが、現実装では追加フィールドが増えています（既存 JSON と互換性は保っているものの、新規キーが入ります）。  
  → Blueprint を別ファイルに切り出す／追加キーを抑止する必要があれば要調整です。

**工程2 prepare**
- 現実装では `--template-spec`（Blueprint 含む `template_spec.json`）を必須にし、Blueprint に基づき slot ごとのカードを生成します。`jobspec.json` は参照していません。
- 生成結果はこれまで通り `prepare_card.json` 等で、`generate_ready.json` は出力していません（従来フローを踏襲）。  
- 生成AI呼び出しは slot 単位のループに拡張しておらず、従来通りの章単位生成（既存オーケストレータ）なので「1ページずつ生成AIを呼ぶ」仕様には未対応です。
- ご提示の「jobspec.json を入力にして slot 生成」「工程2で generate_ready.json を出力」の方針とは乖離があります。こちらを採用する場合、工程2のインターフェースと成果物構成を変更する追加作業が必要です。

**工程3 compose / mapping**
- Static モードでは、工程2で生成したカード＋Blueprintから直接 `draft_approved.json` / `generate_ready.json` を組み立て、レイアウトスコアリングや追加 AI 呼び出しは停止しています（ご要望通り）。  
- ただし、Stage2 で `generate_ready.json` を用意しないため、compose は“Blueprint ベースの generate_ready をその場で確定する”振る舞いです。

**工程4**
- 無変更で設計と一致しています。

**動的モード (baseline)**
- `prepare` は従来通り章リストを生成し、カード数分 LLM 呼び出しが発生します（厳密には「全体1回」ではなくカード単位）。  
  → 「全体で1回のみ」の仕様を求める場合は、既存 generate_document の呼び出しを整理する必要があります。
- `compose` での AI 呼び出し（レイアウト推薦など）は従来通り動作します。

---

**差分サマリ**
1. Stage1 で Blueprint 情報を `template_spec.json` に埋め込んでいる点（新規キー追加）。  
2. Stage2 static モードは `jobspec.json` ではなく `template_spec` の Blueprint を参照し、`generate_ready.json` は出力していない。  
3. static モードでも LLM 呼び出しは従来の章単位で、slot 単位の 1 ページずつ生成にはなっていない。  
4. 動的モードの LLM 呼び出し回数も従来通りカード単位。

これらの差分を埋める方向（例えば Stage2 で `jobspec` を参照・`generate_ready.json` を出力、LLM 呼び出し単位の変更、Blueprint の別ファイル化 等）でよろしければ、追加タスクとして具体化しますのでお知らせください。

template_spec.json, jobspec.json, layouts.jsonl の違いを教えてください。
（modeに）

1. >  - ただしモードごとに異なるファイルを指定させたくない意図は理解しました。現状はどのモードでも template_spec.json・jobspec.json・layouts.jsonl が揃っている想定なので、静的モードでも同じ一式を使えるよう、Blueprint も jobspec.json へ寄せる（あるいは参照先を揃える）方向を検討します。
jobspec.json にはmeta.layouts_pathがあり、依存するlayouts.jsonlがどこにあるかを紐付けしている。同様にtemplate_spec.jsonも紐付けるだけで、Blueprintをjobspec.jsonに寄せる必要はなくなりますかね。

3. 認識合いましたね。では対応不要です。

4. > 4. 動的モードの LLM 呼び出し回数も従来通りカードごとに発生。
これは私の要望に変更して

- `jobspec.json` の `meta` に既に `layouts_path`・`template_path` を保持しているので、同じ流儀で Blueprint 元の `template_spec_path`（仮称）を追加すれば、モード問わず一式のファイルを使い回せます。Blueprint 自体を `jobspec` に移す必要はなく、参照先を統一するだけで意図は満たせそうです（Stage1 で `template_spec.json` を出力 → Stage2/3 は `jobspec.meta.template_spec_path` を辿って Blueprint を読む流れ）。この方向でドキュメント・実装を詰めますね。  
- 静的モードのカード生成方式は共通認識で問題なし（対応不要）。  
- 動的モードの LLM 呼び出しを「全体1回」に集約する改修を次のタスクとして進めます。

はい、お願いします。
