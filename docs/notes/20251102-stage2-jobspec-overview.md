# 2025-11-07 stage 2〜4のジョブスペック運用見直しメモ

> 注記: stage 5 の CLI は 2025-11 時点で `pptx gen` に統一されており、本メモに登場する `pptx render` は検討当時の案です。

## 調査背景
- ユーザー要望: 「ジョブスペック作成を人手作業から脱却し、stage 2 でテンプレート抽出と合わせて生成したい」
- 現行想定: ジョブスペックは stage 3 に入る前のヒト作業で整備し、stage 3〜5で共通入力として利用している。
- 並行中のドキュメント整備が完了するまで実装変更は保留する前提で、現状把握と再設計案を整理した。

## 現状確認
- サンプルファイルの構造差分
  - `samples/json/sample_jobspec.json` には `meta`（案件タイトル・クライアント・テーマなど）、`auth`（作成者、部門）、`slides`（スライド ID・レイアウト名・アンカー・画像パス等）が含まれ、テンプレートのプレースホルダー情報まで埋め込まれている (`samples/json/sample_jobspec.json:1-57` など)。
  - `samples/prepare/prepare_card.json` は stage 3 の成果物を保持し、カードごとに `role.story_phase` / `role.intent_tags` / `content.title` / `content.body[]` / `content.notes[]` を含むが、レイアウトアンカーなどテンプレ依存情報は含まない。
  - 差分の意味: stage 3 以降で同じ `slide_id` をキーに統合するため、ジョブスペック側にテンプレと整合する構造情報が必要になる。
- ジョブスペックが参照される stage
  - stage 3: `uv run pptx prepare ...` がジョブスペックを参照しつつプレペア成果物を生成する際のベースになる (`README.md:96-109`)。
  - stage 4: `uv run pptx outline ...` が章構成とページ順を決める際にジョブスペックの `slides` 配列を参照し、`layout_hint` などの候補提示に利用する (`README.md:111-121`)。
  - stage 5: `uv run pptx mapping ...` がジョブスペック＋承認済みコンテンツを結合して `generate_ready.json` を生成する際、レイアウト名・アンカー・画像指定をジョブスペックから取得する (`README.md:123-140`)。
- stage 1/2で得られる情報
  - stage 1（テンプレ準備）はテンプレート PPTX の管理・命名・バージョン整理に専念しており、ジョブスペックのようなスライド構造データは生成しない (`README.md:51-62`)。
  - stage 2（テンプレ構造抽出）は `uv run pptx tpl-extract ...` や `layout-validate` でレイアウト構造・アンカー・ブランド設定を JSON / YAML 化するが、生成されるのは `layouts.jsonl`・`branding.json` 等であり、ジョブスペック形式の `slides` 配列は出力されない (`README.md:63-95`)。
- ドキュメント記載との整合
  - `docs/requirements/stages/stage-03-content-normalization.md` はジョブスペックを stage 3 の入力（プレペア整形済みデータ）と位置付け、HITL 承認後に `prepare_card.json` を生成する流れを定義。
  - `docs/design/design.md:34-60` も「stage 3: プレペア正規化（HITL）が `spec.json` とテンプレ構造を参照しつつ `prepare_card.json` を作る」前提でアーキテクチャ図を記載しており、ジョブスペックは stage 3 より前に人が整備する想定になっている。

## 再設計案（ユーザー要望ベース）
- stage 2 でジョブスペック雛形を生成する案
  - テンプレ抽出結果（`layouts.jsonl` のレイアウト用途タグ・アンカー一覧）からページ単位のテンプレート集を構築し、`slide_id` / `layout` / アンカー情報を自動採番したジョブスペック雛形 (`spec_scaffold.json` 等) を生成する。
  - ジョブスペック雛形は章構成やスライド順を含まないテンプレートカタログ的なデータとし、本文やメッセージ領域は空欄（またはプレースホルダ説明のみ）で出力する。
- stage 3 (生成AI) の位置づけを調整
  - 案件側の生情報を入力に、生成AIが章構成案・スライド順・各ページのメインメッセージおよび支えるコンテンツ候補を整理したプレペア（抽象カード集合）を作成する。
  - テンプレとのマージは行わず、`prepare_card.json` や関連ログをテンプレ非依存の構造として出力する。
  - stage 3 出力にはストーリーフェーズ・意図タグ・メッセージアングルなど既存要件 (`docs/requirements/stages/stage-03-content-normalization.md:3-45`) を維持。
- stage 4 (生成AI) の役割再定義
  - stage 3 で作成したプレペア（抽象カード）と、stage 2 のジョブスペック雛形／テンプレ構造 JSON をマージし、`layout_hint` やページ割り当てまで具体的に埋めた `draft_approved.json` を生成する。
  - 現行仕様にある HITL 差戻し管理・章テンプレ適用 (`docs/requirements/stages/stage-04-draft-structuring.md:1-120`) を前提にしつつ、生成AIの補助で「ほぼ形にした成果物」を出す方向を目指す。
- stage 5 以降は現行フローを維持
  - `pptx mapping` → `pptx render` の自動処理で品質ゲートと最終出力を担保する。
- 実装着手タイミング
  - 現行ドキュメント整備が完了した後に詳細 Plan（仕様変更箇所・CLI追加案・テスト方針）をまとめ、承認を得てから実装に進む。

## 保留事項と次のアクション
- stage 3 で扱う入力定義
  - 生成AIがプレペアを構築する際に参照するユーザー入力（テキスト資料、メモ、要件定義など）の形式や最低限必要な情報を整理する。
  - 既存サンプル（旧コンテンツ承認 JSON など）との互換性を考慮し、ストーリー情報や intent タグをどの段階で付与するか明確化する。
- CLI / API 影響範囲
  - 新規ラッパーコマンドの追加、`pptx prepare` や `pptx outline` の引数変更、`pptx gen` のスコープ変更が発生するため、既存ドキュメント・テストの更新が必須。
  - API（stage 3/4のHITL管理）にジョブスペック自動生成をどう組み込むか検討が必要。既存エンドポイントとの整合性を確認する。
- ドキュメント更新計画
  - `README.md`、`docs/design/design.md`、`docs/requirements/stages/*.md` の stage 説明を刷新する必要がある。
  - 並行整備中ドキュメントが更新完了した後、本メモを元に体系的な更新 Plan を作成し、 Approval-First Policy に従って承認を得る。

## stage 5（マッピング）の必要性調査
- 要件ドキュメントの確認
  - `docs/requirements/stages/stage-04-mapping.md` は、stage 4 の出力として `generate_ready.json`・`mapping_log.json`・（必要に応じて）`fallback_report.json` を要求し、必須プレースホルダー充足やフォールバック履歴、Analyzer サマリを品質ゲートとする設計を明記。
  - 同ドキュメントは「レイアウト候補スコアリング」「AI 補完」「フォールバック適用」「監査ログ収集」を stage 5 の責務としており、stage 4 には含まれない。
- stage 4 との責務境界
  - `docs/requirements/stages/stage-04-draft-structuring.md` は HITL stage として章構成・`layout_hint` の確定、差戻し理由管理、章テンプレ適用率などを扱う。プレースホルダーの具体的割付や自動補完、監査ログ生成は扱っていない。
  - stage 4 で出力される `draft_approved.json` には `layout_hint` は含まれるが、テンプレのアンカーごとにどの要素を入れるかは未決定であり、stage 5 でのルール／AI 処理が必要。
- stage 5 との連携
  - `docs/requirements/stages/stage-05-rendering.md` は入力として `generate_ready.json` を前提としており、そこに `job_meta` / `job_auth` や PH→要素マッピングが埋まっていることを要求。stage 4 を取り除くと、stage 5 が自前で割付・検証・監査ログ生成まで担う必要が生じ、責務が過大になる。
  - 監査ログ (`audit_log.json`) は stage 5 が出力する `mapping_log.json` を参照してフォールバック履歴や警告を記録する設計になっているため、stage 5 を省くと監査フローが破綻する。
- 2段階品質ゲートの意義
  - 実務では stage 4 完了後も stage 5 でエラーが出れば stage 4 へ戻って差戻しを行うが、これは「HITL 承認済み構成」がまず提出され、その後「自動割付が完了し品質ゲートを通過した」ことを確認する二段階の審査になっている。
  - stage 5 を残すことで、プレースホルダー割付の失敗やフォールバック適用有無を自動的に検出し、レンダリング（stage 6）へ進む前に失敗理由をログにまとめられる。
- 結論
  - stage 4 でテンプレ JSON をマージして出力する新デザインを検討しても、stage 5 が担う品質ゲート・監査ログ・再実行ポイントは依然として必要。
  - よって stage 5 はステージとして存続させ、stage 4 の成果物を品質保証・監査可能な状態へ仕上げる役割を維持する。

## コマンド構成の方向性メモ
- `uv run pptx gen` の役割を stage 5（レンダリング＋Polisher＋PDF 変換）に限定し、スコープを明確化する。従来の「stage 4→5 合体モード」から絞り込み、引数解釈や監査ログ出力をレンダリング専用にする。
- stage 4+5をまとめて実行するラッパー CLI（仮称: `pptx prepare` など）を新設し、HITL 承認済みコンテンツから `generate_ready.json` までを一括で生成できるユーザ体験を提供する。内部では既存 `pptx outline` → `pptx mapping` を順に呼び出し、ログやエラーを統合出力する想定。
- ラッパー導入後も個別コマンド（`pptx outline`, `pptx mapping`）は残し、CI/デバッグ用に stage 単位で再実行できるようにする。特に stage 5 単体の再実行はフォールバック検証や性能計測で有用なため、引き続きサポートする。
- コマンド再設計に伴い、ドキュメント更新（`README.md`, `docs/design/design.md`, `docs/runbooks/` 系）とテストケースの見直し（CLI 統合テスト、CI スクリプト）が必要。仕様反映のタイミングは並行ドキュメント整備完了後に Plan を作成し、承認のうえ実施する。

## stage 2 コマンド運用メモ
- `pptx tpl-extract` の目的: テンプレート PPTX からレイアウト構造 (`layouts.jsonl` ベース) とブランド設定 (`branding.json`) を抽出し、stage 3 以降で消費できるデータを生成する。抽出結果だけを別処理へ渡す用途もあるため単機能化されている。
- `pptx layout-validate` の目的: 抽出済みデータに対してスキーマ検証・差分診断・Analyzer スナップショットとの突合を行い、警告・エラーを `diagnostics.json` や `diff_report.json` に記録する品質ゲート。CI や回帰テストでの再実行を想定し、実行有無を柔軟に制御できるよう独立コマンドとして提供している。
- ユーザビリティ観点では抽出直後に検証をまとめて行いたいニーズがあるため、`tpl-extract` に `--validate` のようなオプションを追加して連続実行するラッパー機能を検討する余地がある。ただし現状は責務分離を維持し、必要に応じて手動で 2 コマンドを順に実行する運用となっている。

## 次ステップ（ロードマップ項目）
- RM-044: stage 2 でジョブスペック雛形（spec scaffold）を自動生成するテーマ。
- RM-045: stage 2 の `tpl-extract` と `layout-validate` 実行を統合するラッパー／オプション整備。
- RM-046: stage 3 で生成AIが案件プレペアを整理するワークフロー整備。
- RM-047: stage 4 でプレペアとテンプレ構造 JSON をマージし、`layout_hint` 付きドラフトを生成するテーマ。
- RM-048: stage 4+5 を連続実行するラッパー CLI 整備。
- RM-049: `pptx gen` を stage 6 専用（レンダリング）に絞り、コマンド体系を再整理するテーマ。
