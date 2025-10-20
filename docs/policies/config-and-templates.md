# 設定・テンプレート管理ポリシー

## 対象範囲
- `config/branding.json`, `config/rules.json` など設定ファイル全般
- `.pptx` テンプレートおよび `rules/polish.yaml`
  ※テンプレートは .pptx のみ対応（.potxは未対応）。.potxを利用したい場合はPowerPointで新規 .pptx として保存してください。

## 変更手順
1. 変更内容を ToDo に記録し、影響範囲を整理する。
2. Pull Request でレビューを受けるまで `draft` 状態を維持する。
3. レビューコメントは 24 時間以内を目安に対応し、議論の結果は PR に明記する。

## branding.json の構造
- スキーマバージョンは `version: "layout-style-v1"` を既定とする。後続の拡張ではバージョンを更新し、互換性の有無をドキュメント化する。
- `theme` 配下でブランド共通のフォント (`fonts.heading` / `fonts.body`) と基調色 (`colors.primary` など) を定義する。フォントには `bold` / `italic` も指定できる。
- `components` 配下で要素別スタイルを管理する。
  - `table`: フォールバック配置 (`fallback_box`)、ヘッダー／本文のフォントと塗りつぶし色、ゼブラ配色を定義。
  - `chart`: カラーパレット、データラベル既定値、軸フォント、フォールバック配置を定義。
  - `image`: フォールバック配置と既定の `sizing` モードを定義。
  - `textbox`: フォールバック配置、既定フォント、段落スタイル（揃え・行間・段落前後余白・インデント）を定義。
    - インデントはインチ単位で `left_indent_in` / `right_indent_in` / `first_line_indent_in` を指定し、Renderer が段落レベルに応じた余白を正しく適用できるようにする。
- `layouts` にレイアウト名ごとの `placements` を登録すると、アンカー未指定時に要素 ID 単位で配置やフォントを上書きできる。
- 詳細な設計背景と運用ルールは [docs/design/layout-style-governance.md](../design/layout-style-governance.md) を参照する。

## rules.json の構成
- `title.max_length` / `bullet.max_length` / `bullet.max_level` は従来通りタイトル・本文の長さと階層を制御する。
- `forbidden_words` は禁則語を列挙し、バリデーションで一致したテキストを拒否する。
- `analyzer` セクションでは自動診断の閾値を管理する。
  - `min_font_size`, `default_font_size`: 箇条書きの最低フォントサイズと既定サイズ。
  - `default_font_color`, `preferred_text_color`, `background_color`: コントラスト判定と修正提案で利用する色設定。
  - `min_contrast_ratio`, `large_text_min_contrast`, `large_text_threshold_pt`: WCAG 基準に基づくコントラスト判定値。
  - `margin_in`, `slide_width_in`, `slide_height_in`: 余白チェックに使用する寸法。
- `refiner` セクションでは自動補正（Refiner）の適用可否と閾値を制御する。
  - `enable_bullet_reindent`: 箇条書きレベルの再調整を有効化。
  - `enable_font_raise`, `min_font_size`: フォントサイズを下限まで引き上げるかどうかと閾値。
  - `enable_color_adjust`, `preferred_text_color`, `fallback_font_color`: 文字色をブランドカラーへ合わせる際の挙動。
- `refiner` のカラー調整を有効化する場合は、ブランド設定 (`config/branding.json`) と整合する色を指定する。

## バリデーション
- テンプレート更新時は次のコマンドで抽出結果と差分を検証する。
  ```bash
  uv run pptx tpl-extract \
    --template templates/libraries/<brand>/<version>/template.pptx \
    --output .pptx/extract/<brand>_<version>

  uv run pptx layout-validate \
    --template templates/libraries/<brand>/<version>/template.pptx \
    --output .pptx/validation/<brand>_<version> \
    --baseline releases/<brand>/<prev_version>/layouts.jsonl
  ```
  - `tpl-extract` で最新テンプレのレイアウト仕様と `branding.json` を生成し、保管する。
  - `layout-validate` で `layouts.jsonl` と `diagnostics.json` を検証し、ベースラインとの差分レポート (`diff_report.json`) を確認する。致命的エラーが検出された場合は exit code 6 で停止する。
- 設定ファイルは `jsonschema` に基づく検証スクリプト（未整備の場合は CLI で手動検証）を実施する。

## テンプレート利用要件
- CLI の `--template` オプションで指定できるのは `.pptx` ファイルのみ。.potx は PowerPoint で新規 `.pptx` として保存し直す。
- JSON 仕様の `layout` はテンプレート内のレイアウト名と一致させる。不一致時は既定レイアウトが利用されるため、意図した構成を反映したい場合はテンプレート側の名称を確認する。
- 画像・表・グラフなどを特定位置へ差し込みたい場合は、テンプレートの図形またはプレースホルダーに一意な名前を付けて JSON の `anchor` に同じ名前を記載する。アンカーが無い場合は既定のフォールバック座標に配置される。
- 色やフォントはスライドマスターの設定ではなく `config/branding.json` を参照して適用される。テンプレート側でフォントや配色を変えても自動では反映されない点に注意する。
- 利用者向けテンプレートは `templates/` ディレクトリ配下に管理し、案件固有のテンプレートは `samples/` など任意の場所に置いたうえで CLI 実行時にパスを明示する。
- 具体例として、`samples/templates/templates.pptx` にレイアウト名とアンカー命名例を添付している。
- 画像は連携済みロゴのみを想定する。写真・アイコンなど任意画像はテンプレート側に含めず、必要に応じて後工程で人手挿入とする。チャートはテキストで構造化可能なデータのみ表形式で表現する。

### サンプル準拠レイアウト（参考）
| layout 名 | 想定用途 | 主なアンカー |
| --- | --- | --- |
| `Title` | ビジュアル付きカバー。タイトル／サブタイトル＋ `cover-visual`・`brand-logo` | `cover-visual`, `brand-logo` |
| `Agenda` | アジェンダ一覧。本文プレースホルダー＋マイルストーン表 | `milestone-table`, `agenda-visual` |
| `Two Column Detail` | 2 カラム構成の詳細説明。左に箇条書き、右に画像 | `detail-visual` |
| `One Column Detail` | 1 カラム構成でメッセージ重視。必要に応じて下部に画像 | `detail-visual` |
| `Closing` | クロージング＋CTA。箇条書きとロゴ／ボタン | `closing-cta` |

> ※最小構成サンプルでは PowerPoint 既定の `Title Slide` / `Title and Content` レイアウトを利用。

### アンカー命名と管理
- 図形名は PowerPoint の「選択ウィンドウ」（mac: `Cmd+Shift+F10`, Windows: `Alt+F10`）で変更する。複製後は同名のままになりやすいので必ずリネームする。
- `anchor` は日本語でも動作するが、JSON とテンプレートで完全一致させる。1 スライド内に同名アンカーが複数あると先に見つかった図形だけが使われる点に注意する。
- プレースホルダーを利用する場合は、スライドレイアウト側で名前を付けておく。生成されたスライドで既定名に変換されても、レイアウトに設定した名称で参照される。
- レンダラーはレイアウト上のプレースホルダー名をアンカーとして解決し、配置時にはプレースホルダーの座標・サイズをそのまま引き継ぐ。生成後もプレースホルダーは削除されないため、レイアウト編集用の目印として維持される。
- プレースホルダーに初期テキストが残っていると生成物に重なる場合があるため、アンカー用途のプレースホルダーは空文字にしておくかテンプレート側でダミー文字を削除しておく。
- テーブルやチャートの差し込み位置は、名前付きプレースホルダーを優先して利用できる。既存テンプレートにプレースホルダーが無い場合はアンカー用の図形（長方形など）を配置し、`timeline-table` や `metric-chart` のように命名する。図形は透明にしておくとテンプレートとして扱いやすい。
- レイアウト間で同じアンカー名を再利用することは可能（各スライドで独立して探索される）が、同一レイアウト内では一意になるよう整理する。

## テンプレート準備チェックリスト
- スライドマスターに JSON 仕様で使用する `layout` と同名のレイアウトを登録し、必要なアウトラインを網羅する。
- 各レイアウトのテキスト枠や図形は位置・サイズを確定させ、不要なプレースホルダーを削除する。
- 差し込み対象の図形・テキスト枠には一意な名前を設定し、JSON から `anchor` として参照できるようにする。
- 配色やフォントは `config/branding.json` が適用する前提で整え、テンプレート側で固定値を埋め込まない。
- 画像・アイコンなど差し替えが想定される領域にはダミー枠を配置し、同じくアンカー名を付与する。
- 想定ストーリー（タイトル、アジェンダ、セクション、まとめ等）に対応したスライド種別が不足していないか確認する。
- `.pptx` 形式で保存し、`soffice` など外部ツールで開いた際に不要なサンプルスライドやメタ情報が残っていないか点検する。

## 追跡と記録
- 重大な意思決定やテンプレート更新理由は `docs/adr/` に記録する。
- リリースノートにはユーザー影響がある設定変更を必ず含める。
- 作業ログは対応した ToDo ファイルに残す。

## ドキュメント更新のチェックリスト

### ToDo 追加時のルール
- `docs/todo/` に新規ファイルを作成したら、必ず当日中に `docs/roadmap/roadmap.md` を更新し、テーマと状況を追記する。
- ロードマップの更新有無はコミット時に確認し、未反映の場合は差し戻す。
- 必要に応じて、ロードマップに「次のアクション」を具体的に記載する。

### 既存ドキュメント更新時のルール
- README やノート類に関わる更新を行った場合は、関連する ToDo にメモや進捗を追記する。
- 設計ノート（`docs/notes/`）は、作業完了時に参照リンクを ToDo メモ欄へ追加する。
- ロードマップの状況欄は「完了項目数 / 総項目数」で管理する。

### レビュー時のチェック観点
- 新しい ToDo がロードマップに未掲載になっていないか。
- ロードマップの状況欄が最新の進捗と一致しているか。
- メモに記されたリンク（ノートや PR）が実在するか。
