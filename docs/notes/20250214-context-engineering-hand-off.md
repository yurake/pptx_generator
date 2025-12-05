# コンテキスト設計ポリシー検討ノート (2025-02-14)

## 背景
- Anthropic の以下の記事を参照し、リポジトリ内ドキュメントの構造と運用指針へ取り入れる方針を検討した。
  - [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  - [Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- 目的は、README / AGENTS / `docs/` 配下の資料を「必要な情報を必要なタイミングで参照できる」形式に揃え、エージェント作業時の前提・参照フローを明確にすること。

## ここまでの整理内容

### 基本ポリシーとして取り込む方針
1. **すべてを upfront コンテキストへ詰め込まない**  
   - README / AGENTS はサマリまでに留め、詳細は Runbook や Design などの参照リンクで提供する。
2. **オンデマンド参照の推奨**  
   - `rg` / `glob` を活用し、必要なファイルを検索して読む手順を明文化する。
3. **ルールとドキュメントを階層構造で管理**  
   - 既存カテゴリ（policies → requirements → design → runbooks → notes）の読み順を守る指針を追加する。
4. **必要な情報を必要な時だけ注入**  
   - Plan / ToDo には参照する資料のリンクのみを記載し、作業中に詳細を都度確認する運用へ寄せる。

### 既存ドキュメントの現状メモ
- `README.md`: stage・コマンドが詳細に記載されている。冒頭サマリとドキュメント索引を追加する余地あり（まだ未実施）。
- `AGENTS.md`: タスク運用や ToDo 連携を中心に説明。コンテキスト整理ルールの追記が必要。
- `docs/README.md`: カテゴリ一覧は存在。各カテゴリの役割を State/History/Goals 形式で補足する案がある。
- Runbook: 入力・手順・失敗時対応が揃っているものとそうでないものが混在。

### ToDo / Plan 運用への影響
- Plan 承認後に ToDo の「設計・実装方針の確定」で方針メモを記載し、関連ドキュメント（Runbook / Design 等）へのリンクを明示する運用を強化する予定。
- ToDo テンプレートへ「設計・実装方針メモの共有」チェック欄を追加し、参照資料のリンク先を記す案を検討中（まだ未反映）。

## 次に実施するべきタスク案（RM-069 として管理）
1. **policies へのポリシー文書追加**  
   - `docs/policies/context-engineering.md`（仮）を作成し、上記 4 ポイントと README / AGENTS 構成テンプレ、ルール読み順を明文化する。
2. **README / AGENTS の冒頭刷新**  
   - 「目的 → 主要入力 → 主な出力 → 制約 → 参照資料 → チェックリスト」の順に再構成するドラフトを作成。
3. **Runbook のテンプレート化**  
   - 代表的な Runbook を「前提」「入力」「手順」「失敗時」「関連資料」の欄で統一する（既存ファイルの差分調査が必要）。
4. **ToDo テンプレートの更新**  
   - 設計・実装方針メモと参照資料リンクを記載するチェック欄を追加し、Plan → 実装までの流れを強制できるよう調整。
5. **サンプル作業フローのドキュメント化**  
   - 例: 「静的 Blueprint パイプラインを実行する場合」に、README → Runbook → ToDo の順でどの資料を参照するかをガイドとして残す。

## 補足メモ
- 既存の README / AGENTS を即時に書き換えるのではなく、ガイドライン整備 → 段階的反映の順で進めるのが安全。
- Runbook がスキルの原型になる想定で整理しておくと、将来的に自動化が必要になった際にも対応しやすい。
- 変更反映時は ToDo を作成し、設計・実装方針メモに参照資料と要約を記載する運用を徹底する。

---

## 2025-11-28 更新メモ
- `docs/policies/context-engineering.md` を新設し、Upfront サマリ・オンデマンド参照・階層管理・タスク分離の 4 原則を明文化した。
- README / AGENTS / `docs/README.md` をサマリ中心の構成へ刷新し、詳細は下位ドキュメントへ誘導する運用へ切り替えた。
- `docs/policies/task-management.md` に Plan／ToDo 記述時の参照資料リンクを明示する項目を追加した。
- 今後のドキュメント更新では、各カテゴリ README と ToDo のメモ欄で参照リンクを明示し、Plan 承認メッセージを記録する運用を継続する。

別の方に同様の相談をした際のコメントを転記します。検討の参考としてください。

# Q
coding agentを利用したプロジェクト開発における、context engineeringの導入について調査してほしい。生成AIに渡すcontextを適切に制御することで、余剰なトークン利用によるコスト増を抑え、contextが多くなることで欠損やハルシネーションが起こるリスクを低減し、生成AIがより高度に指示に従うようにするには、プロジェクトではどのようにcontextを管理するのがベストかを知りたい。その上で、私が開発するyurake/pptx_generatorプロジェクトへ反映したい。

# A
結論からいうと、

* 「コンテキストは全部突っ込む」ではなく
* プロジェクト側で **階層化されたコンテキスト設計＋Retrieval（必要な時だけ取り出す）＋要約／分離ルール** を持つのが、
  coding agent 時代のベストプラクティスにかなり近いです。

そのうえで、今の `yurake/pptx_generator` は AGENTS.md / CLAUDE.md / docs がかなり充実しているので、
「どのタスクでどの文書・ソースを読ませるか」を明示する薄いレイヤを足せば、かなり綺麗に context engineering できます。

---

## 1. coding agent 文脈での context engineering 概観

最近は、prompt engineering より一段上のレイヤとして、

* **Write（書きためる）**
* **Select（必要なものだけ選ぶ）**
* **Compress（要約する）**
* **Isolate（タスクごとに分離する）**

という 4 操作でコンテキストをマネジメントする枠組みがよく使われています。([LangChain Blog][1])

また、LLM への入力を「情報ペイロード」と見なし、

* どの情報を
* どの粒度で
* どのタイミングで渡すか

を設計・最適化すること自体を、**Context Engineering** という独立した設計領域として整理する動きも出ています。([arXiv][2])

Anthropic や LangChain などのエージェント系の文献・記事をざっと見ると、共通しているポイントはだいたい次の 3 つです。([Anthropic][3])

1. **常に全部突っ込まない**
   → コンテキストウィンドウは有限で、入れすぎると「大事なところが埋もれる＋コスト爆増＋ハルシネーション増加」。

2. **Retrieval / 検索前提のアーキテクチャにする**
   → コードベース・ドキュメントから「いま必要な部分だけ」取ってくる仕組み（grep, LSP, embeddings, RAG, MCP など）を前提に設計する。([Sourcegraph][4])

3. **コンテキストを階層化する**
   → 「グローバル方針」「プロジェクト仕様」「タスクローカルなメモ」を明確に分け、それぞれ別の更新・読み込み戦略を持つ。([arXiv][5])

---

## 2. コーディングエージェント向けの代表的パターン

### 2-1 Write / Select / Compress / Isolate

LangChain や各種ガイドでは、エージェントのコンテキスト戦略として次の 4 つが軸とされています。([LangChain Blog][1])

* **Write**

  * 意思決定・設計・ユーザの好みなどを、「後で再利用できるテキスト」として書き残す（README, AGENTS.md, 仕様書, 変更ログなど）。
* **Select**

  * あるタスクに必要な情報だけを検索・フィルタして取り出す（コード検索・文書検索・ベクトル検索）。
* **Compress**

  * 長いログや設計資料を、エージェントが扱いやすい要約に落とし込む（セッション要約、PR 要約、モジュール要約）。
* **Isolate**

  * タスクごとにコンテキスト空間を分ける（サブエージェント、ブランチごとのメモ、フォルダ単位のスコープなど）。

ここに、Anthropic の「エージェントの thinking budget を明示的に制御し、どこまで考えるか／どこで外部ツールに投げるかを設計する」という考え方が乗ってきています。([Anthropic][3])

### 2-2 階層的コンテキスト（hierarchical context）

Git-Context-Controller のような研究では、

* 高レベル計画
* コミットレベルのサマリ
* 実行トレース

の 3 層に分けてコンテキストファイルを管理するアーキテクチャが提案されています。([arXiv][5])

coding agent で実務に落とすなら、もう少し実装寄りに：

1. **プロジェクト全体の原則・制約**

   * 開発方針、命名規約、テストポリシー、CLI の非機能要件など
   * → `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` などで管理

2. **ドメイン別・stage 別の仕様／設計**

   * pptx_generator でいうと、テンプレ / コンテンツ準備 / マッピング / レンダリングごとの要件・設計文書
   * → `docs/requirements/stages/*` `docs/design/stages/*` など

3. **タスクローカルな情報**

   * 「この PR の目的」「このバグの再現手順」「この refactor の範囲」など
   * → PR description, issue description, ローカルの `notes/*.md` など

4. **コード・テスト・スキーマそのもの**

   * 実際に修正対象となる関数・クラス・テスト・JSON schema 等
   * → retrieval 経由で必要部分だけ読み込む

この 1〜4 をごちゃ混ぜに一気に投げるのではなく、
**「いまは 1 と 2 だけ」「次に 3 と 4 をスポットで」**という段階的ロードがポイントです。

### 2-3 Retrieval-first なコードコンテキスト

Sourcegraph などの coding assistant ベンダーは、コンテキスト管理の本質は「検索品質」と強調しています。([Sourcegraph][4])

* 単純な「N 行前後」ではなく、

  * 依存グラフ（呼び出し関係）
  * git 履歴（最近変更された部分）
  * embeddings やシンボルインデックス

など複数シグナルで「いまの質問に最も関係が深いコード片」を選び、最小限に絞って渡す、という戦略です。

Google や他のベンダーのベストプラクティスでも、
まずは README や docstring をきちんと書いておき、それを軸に AI がコードを引けるようにする「コンテキストのための基盤整備」が強く推奨されています。([Google Cloud][6])

### 2-4 サブエージェントでコンテキストを分離する

Claude Code では、**custom subagents がコンテキスト管理の最強機能の一つ**とされています。([Anthropic][7])

* メインエージェントには「タスクのゴール」と最低限のリポジトリ方針だけを渡す
* 実際のコード探索や設計ドキュメントの読み込みは、

  * 「template-pipeline-agent」
  * 「mapping-agent」
  * 「rendering-agent」
    などのサブエージェントが担当
* 各サブエージェントは、担当フォルダ／担当 docs だけを既定コンテキストとして持つ

という形にすることで、

* 1 つのタスクに必要な X, Y, Z トークンを、
  メインで全部持たせるのではなく「サブエージェント側に分散」して、
  メイン窓のトークンを節約する、という設計です。([blog.sshh.io][8])

---

## 3. プロジェクト開発での「ベストな」コンテキスト管理アーキテクチャ（汎用）

上の知見を踏まえて、coding agent 前提のプロジェクトでおすすめできる構成を、少し抽象化して書きます。

### 3-1 レイヤ設計

1. **Global / Org レイヤ（不変に近い）**

   * チーム共通ポリシー、Git / CI ルール、Conventional Commits、ライセンス方針など。
   * → 別リポの `global-AGENTS.md` や社内 Wiki にまとめ、個別プロジェクトの AGENTS.md から参照リンクだけ張る。

2. **Project レイヤ（pptx_generator 単位）**

   * プロジェクトの目的、ドメインモデル、全体アーキテクチャ、CLI パイプライン、用語集。
   * → `README.md`, `docs/design/design.md`, `docs/requirements/requirements.md`, `AGENTS.md` など。

3. **Subsystem / Stage レイヤ**

   * 「テンプレ」「コンテンツ準備」「マッピング」「レンダリング」など、stage 別の仕様・設計・運用ガイド。
   * → `docs/requirements/stages/*`, `docs/design/stages/*`, `docs/runbooks/*`。

4. **Task レイヤ（PR / Issue / ローカルノート）**

   * このタスクで何をするのか、どのファイルを触るのか、前提となる仕様はどれか、など。
   * → GitHub Issue/PR description, `docs/notes/*`, ローカルの `/notes`。

5. **Code / Schema / Tests レイヤ**

   * 実際のコード・テスト・JSON/YAML スキーマ等。
   * → coding agent 側が search / RAG で読み込む。

**方針：**

* coding agent の **初回呼び出し** では 1〜3 を中心に読む。
* タスク指示を与えるときは、4 にプロジェクト内部リンクを集約し、
  5 の具体的なファイルは「パスだけ」教え、実体はエージェントが検索して読む。

### 3-2 運用ルール（ヒューリスティクス）

例えば、以下のような「コンテキスト利用ポリシー」を AGENTS.md に明示しておくと、余剰トークン削減に効きます。

* **原則 1: 1 回のリクエストで読む総トークンの上限を決める**

  * 例: 「コード＋docs 合計 20〜40KB 程度まで」「それを超える場合は要約してから続きに進む」。
  * 有効コンテキスト長をベンチマークして、モデルごとにスイートスポットを探るのも推奨されています。([eval.16x.engineer][9])

* **原則 2: 「仕様 → コード → テスト」の順に読む**

  * 先に仕様・設計を読ませてからコードを見させることで、
    「コードの形に引きずられた誤ったリファクタ」を減らす。

* **原則 3: 差分ベースで会話する**

  * 修正対象ファイルの**差分＋その周辺 50〜100 行程度**を中心に読み込み、
    ファイル全体を毎回送り直さない。
  * 特に PR レビュー系では、Sourcegraph 等の実装経験でも差分中心が推奨。([Sourcegraph][4])

* **原則 4: 長時間のセッションは段階要約する**

  * 1 セッションで大量の会話をしたら、「区切り」で

    * 何を決めたか
    * どのファイルにどんな影響があるか
      を要約し、それを次回セッションの「起点コンテキスト」として渡す。

* **原則 5: ハルシネーション対策として「検証手順」も必ず教える**

  * テストコマンド、CLI 実行例など、「答えを出したあとに何で検証するか」を必ずコンテキストに含める。

### 3-3 コスト・品質モニタリング

Datacamp や LLM コスト最適化の記事では、コンテキスト設計と合わせて **コストと品質をトラッキングすること**が推奨されています。([DataCamp][10])

* メトリクス例

  * 1 PR あたりのトークン総量
  * 1 セッションあたりの平均入力トークン / 出力トークン
  * テスト失敗率（コンテキスト不足・誤理解によるもの）
  * 人手レビューの修正指摘数

---

## 4. `yurake/pptx_generator` への具体的な反映案

ここからが本題です。既存リポの構造を踏まえた、かなり具体的な案を書きます。([GitHub][11])

### 4-1 既存構造（AGENTS.md / CLAUDE.md / docs/*）の活かし方

現状のトップレベルにはすでに：

* `AGENTS.md`
* `CLAUDE.md`
* `tests/AGENTS.md`
* `docs/requirements/*`
* `docs/design/*`
* `docs/runbooks/*`

があり、**context engineering の「Write」がほぼできている状態**です。([GitHub][11])

ここに、次の 2 つを足すとかなり運用しやすくなります。

1. **`docs/context/context-map.md`（または `.json`）**

   * 「どのタスクで、どのドキュメント・ソースを優先的に読むべきか」のマッピング表。

   * 例：

     * テンプレ タスク
       → `docs/requirements/stages/stage-01-template.md`
       → `docs/design/initiatives/template-style-governance.md`
       → `templates/libraries/**/`
     * コンテンツ準備タスク
       → `docs/requirements/stages/stage-02-prepare.md`
       → `samples/input/`
     * マッピングタスク
       → `docs/requirements/stages/stage-03-compose.md` / `stage-03-compose.md`
       → `src/pptx_generator/mapping/**` `templates/**`
     * レンダリングタスク
       → `docs/design/stages/stage-04-gen.md`
       → `src/pptx_generator/render/**` `dotnet/**`

   * coding agent には、
     「タスク種別を伝える → context-map に従って必要な docs / フォルダだけ search させる」
     というフローを徹底する。

2. **`AGENTS.md` の「コンテキスト利用ポリシー」節を強化**

   例として、以下のような小節を追加するイメージです（日本語のまま書いて OK）：

   * 「コンテキストの読み方」

     * まず `README.md` と `docs/design/design.md` をざっと読み、
       `docs/context/context-map.md` でタスクに対応するセクションを確認してから詳細を読むこと。
   * 「コードを読む順番」

     * コードを編集する前に、必ず関連する `docs/requirements/stages/*` と `docs/design/stages/*` を先に読むこと。
   * 「トークン上限」

     * 1 リクエストで同時に読み込むファイルは、
       原則として 4〜6 ファイル / 合計 20KB 程度を目安とし、
       それ以上必要な場合は「要約 → 続き」の 2 ステップに分割すること。
   * 「検証方法」

     * CLI の変更を行った場合は、`uv run pptx <cmd> --help` と、代表的なサンプル (`samples/**`) を用いた E2E テストコマンドを、必ず回答中に明示すること。

### 4-2 サブエージェント設計案（Claude Code / Codex 兼用の考え方）

Claude Code の best practices やサブエージェント活用記事をベースに、pptx_generator 向けのサブエージェント案を整理します。([Anthropic][7])

#### 例: 4 種類のサブエージェント

1. **TemplateAgent**

   * スコープ:

     * `templates/`
     * `docs/requirements/stages/stage-01-*`
    * `docs/design/initiatives/template-style-governance.md`
     * `docs/policies/config-and-templates.md`
   * 役割:

     * テンプレ抽出 (`pptx template`, `tpl-extract`, `layout-validate`, `tpl-release`) 周りの仕様・実装変更。
   * コンテキスト:

     * 上記 docs の要約 ＋ `src` / `dotnet` からテンプレ関係のモジュールだけを検索して読み込む。

2. **ContentPrepareAgent**

   * スコープ:

     * `docs/requirements/stages/stage-02-*`
     * `samples/input/`
     * `src/pptx_generator/prepare/**`
   * 役割:

     * ブリーフ → BriefCard → prepare_card.json 生成のロジックとログ出力 (`brief_log.json`, `brief_ai_log.json`) 周り。

3. **MappingAgent**

   * スコープ:

     * `docs/requirements/stages/stage-03-*`, `stage-05-*`
     * `docs/design/stages/stage-03-compose.md`
     * `src/pptx_generator/compose/**`, `mapping/**`
   * 役割:

     * ジョブ仕様・ドラフトから `generate_ready.json` を作る経路、`mapping_log.json` やフォールバック制御。

4. **RenderingAgent**

   * スコープ:

     * `docs/requirements/stages/stage-04-gen.md`
     * `docs/design/stages/stage-04-gen.md`
     * `src/pptx_generator/render/**`, `dotnet/`, `config/branding.json`
   * 役割:

     * PPTX レンダリングと Polisher 連携（.NET 側含む）。

AGENTS.md / CLAUDE.md には、例えば次のような運用ルールを書けます：

* 「複雑なタスクは、Template/ContentPrepare/Mapping/Rendering のいずれかのサブエージェントに分解して委譲すること」
* 「メインエージェントは、サブエージェントの出した diff とテスト結果を統合し、PR 説明文とリリースノート草案を作ることに専念する」

Codex には Subagent という形がないですが、
「プロファイル別の AGENTS.md（例: `AGENTS.mapping.md`）＋人間の声がけ」で同じパターンを模倣できます。

### 4-3 context-map と組み合わせたワークフロー例

**ケース: `pptx compose` コマンドに新しいオプションを追加したい**

1. あなた:

   * 「MappingAgent を使って、`pptx compose` に `--dry-run` オプションを追加してください。挙動の要件は…」と指示。
2. エージェント側のステップ（AGENTS.md で明記しておく）:

   1. `docs/context/context-map.md` の「stage 3 マッピング」セクションを見る。
   2. 指定された docs を要約し、要件・制約を抽出。
   3. `src/pptx_generator/compose/**` 周辺を search し、CLI entry point を特定。
   4. 修正案を diff で提案。
   5. `uv run --extra dev pytest tests/test_cli_integration.py` などの検証コマンドを提示。
3. あなた:

   * diff とテストコマンドをレビューし、必要なら追加の要件を投げる。

この「エージェントが自力で docs を読みに行くフロー」を、
**context-map＋AGENTS.md によってパターン化しておく**のが context engineering の要諦です。

### 4-4 今すぐやれる TODO リスト

実装コストが低く、効果が大きい順に並べます。

1. **`docs/context/context-map.md` を新規作成**

   * stage 別・タスク別に「読むべき docs / コードフォルダ」を表形式で整理。

2. **AGENTS.md に「コンテキスト利用ポリシー」セクションを追加**

   * 読む順序（README → design → requirements → code）
   * 1 リクエストあたりのファイル数・サイズ目安
   * テスト／検証手順の明示を必須化
   * 長いセッションの要約ルール

3. **CLAUDE.md でサブエージェントの役割とスコープを定義**

   * TemplateAgent / ContentPrepareAgent / MappingAgent / RenderingAgent など。
   * task → agent mapping を書いておく。

4. **主要モジュールに「エージェント向け docstring / comment」を数行足す**

   * 例: `src/pptx_generator/compose/main.py` の先頭に

     * 「このモジュールは stage 3 マッピングの CLI をまとめている」
     * 「参照すべき設計ドキュメントのパス」
       をコメントで書く。
   * これだけで search ベースのエージェントが「どこを読めばいいか」をかなり把握しやすくなる。

5. **Coding agent セッションのトークン利用をざっくり記録**

   * 1 日 / 1 PR 単位で、

     * リクエスト回数
     * 入力／出力トークン合計（ツールが提供する数字で OK）
   * context-map 導入前後で比較し、コスト削減・品質向上を確認する。

---

## 5. まとめ

* 文献レベルでは、

  * Write / Select / Compress / Isolate を組み合わせ
  * コンテキストを階層化・分離し
  * Retrieval-first で「必要なときに必要な分だけ読む」
    という方針が、現状もっとも支持されています。([arXiv][2])

* `pptx_generator` はすでに docs/ や AGENTS.md が非常に充実しているので、

  * `docs/context/context-map.md` のような「コンテキストインデックス」と
  * AGENTS.md / CLAUDE.md の「コンテキスト利用ポリシー」「サブエージェント設計」
    を少し足すだけで、かなり綺麗な context engineering が実現できます。

もし次のステップとしてよければ、

* `docs/context/context-map.md` の「最初のドラフト」をこちらで Markdown で作る
* あるいは `AGENTS.md` の「コンテキスト利用ポリシー節」だけ具体的な文面を生成する

どちらかから着手しましょう。

[1]: https://blog.langchain.com/context-engineering-for-agents/?utm_source=chatgpt.com "Context Engineering"
[2]: https://arxiv.org/html/2507.13334v1?utm_source=chatgpt.com "A Survey of Context Engineering for Large Language Models"
[3]: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents?utm_source=chatgpt.com "Effective context engineering for AI agents"
[4]: https://sourcegraph.com/blog/lessons-from-building-ai-coding-assistants-context-retrieval-and-evaluation?utm_source=chatgpt.com "Lessons from Building AI Coding Assistants: Context ..."
[5]: https://arxiv.org/html/2508.00031v1?utm_source=chatgpt.com "Manage the Context of LLM-based Agents like Git"
[6]: https://cloud.google.com/blog/topics/developers-practitioners/five-best-practices-for-using-ai-coding-assistants?utm_source=chatgpt.com "Five Best Practices for Using AI Coding Assistants"
[7]: https://www.anthropic.com/engineering/claude-code-best-practices?utm_source=chatgpt.com "Claude Code: Best practices for agentic coding"
[8]: https://blog.sshh.io/p/how-i-use-every-claude-code-feature?utm_source=chatgpt.com "How I Use Every Claude Code Feature - by Shrivu Shankar"
[9]: https://eval.16x.engineer/blog/llm-context-management-guide?utm_source=chatgpt.com "LLM Context Management: How to Improve Performance and ..."
[10]: https://www.datacamp.com/blog/ai-cost-optimization?utm_source=chatgpt.com "Top 10 Methods to Reduce LLM Costs"
[11]: https://github.com/yurake/pptx_generator "GitHub - yurake/pptx_generator"
