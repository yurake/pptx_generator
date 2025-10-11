## PPTX テンプレートと branding.json の対応整理（2025-10-11）

### 背景と目的
- `config/branding.json` に記載するスタイル定義を PPTX テンプレートから自動抽出する方針検討の一環として、項目ごとの取得元と抽出手法を整理する。
- 既存メモ（[docs/notes/20251009-template-branding-config.md](20251009-template-branding-config.md)）で洗い出した課題を踏まえ、実装時に必要となる XML パスやライブラリの利用有無を明記する。

### branding.json スキーマとテンプレート由来情報のマッピング
| branding.json 項目 | PPTX 取得元 | 抽出手法案 | 備考 |
| --- | --- | --- | --- |
| `fonts.heading.name` | `ppt/theme/theme1.xml` &rarr; `<a:fontScheme>` の `<a:majorFont>` (`latin/@typeface`, `ea/@typeface`) | python-pptx: `presentation.part.theme.font_scheme.major_font` から取得。東アジアフォント優先。 | latin に設定がない場合、`ea`（East Asian）を fall back。 |
| `fonts.heading.size_pt` | `ppt/slideMasters/slideMaster1.xml` &rarr; `<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr/@sz>` | lxml で XML 解析し、`sz`（1/100 pt）を整数変換して 100 で割る。 | python-pptx は `sz` を公開していないため直接 XML を読む。 |
| `fonts.heading.color_hex` | 同 `<a:defRPr>` 配下の `<a:solidFill>` （`<a:srgbClr/@val>` または `<a:schemeClr>`） | `srgbClr` はそのまま、`schemeClr` はテーマカラーを引き当てて HEX 化。 | `<a:schemeClr val="accent1">` の場合はテーマから RGB を決定。 |
| `fonts.body.name` | `ppt/theme/theme1.xml` &rarr; `<a:minorFont>` | python-pptx: `font_scheme.minor_font` を利用。 | heading と同じ優先順位でフォントファミリを確定。 |
| `fonts.body.size_pt` | `slideMaster1.xml` &rarr; `<p:txStyles><p:bodyStyle><a:lvl1pPr><a:defRPr/@sz>` | XML 解析（1/100 pt） | Body のデフォルト段落スタイルから取得。 |
| `fonts.body.color_hex` | 同 `<a:defRPr>` の塗り設定 | XML 解析 | テーマ参照時は heading と同じ処理を再利用。 |
| `colors.primary` | `theme1.xml` &rarr; `<a:clrScheme><a:accent1>` | python-pptx: `theme_color_scheme.accent1` から `rgb` プロパティを取得。 | 初期案として accent1 を primary とする。 |
| `colors.secondary` | `accent2` | 同上 | ブランドポリシーで異なる場合はオプション化を検討。 |
| `colors.accent` | `accent3` またはテンプレート内で強調に使う色 | `accent3` を既定値にし、CLI オプションで別色を指定可能にする案。 | accent4〜6 の利用状況をスキャンし、ヒューリスティックを調整。 |
| `colors.background` | `slideMaster1.xml` &rarr; `<p:bgRef><a:schemeClr/@val>` または `<p:bg><a:solidFill>` | XML 解析。`schemeClr` の場合はテーマ参照で RGB を決定。 | 背景画像があるテンプレートは別処理が必要。 |
| `footer.text` | `slideMaster1.xml` の `<p:spTree>`（`type="ftr"` の図形テキスト） | python-pptx ではマスター図形にアクセス不可のため、XML を直接パース。 | マスターに埋め込みテキストがない場合は空文字扱い。 |
| `footer.show_page_number` | `slideMaster1.xml` の `<p:showMasterPhAnim>` および `<p:sp type="sldNum">` | XML の `showMasterPhAnim` が `1` かつ `sldNum` プレースホルダーが存在するかで判定。 | 個別スライドで上書きされるケースは要後続検証。 |

### 推奨抽出フロー
1. python-pptx でプレゼンテーションを読み込み、テーマ情報（フォント／カラー）を API で取得。
2. `zipfile` で PPTX を展開し、`slideMasters/slideMaster1.xml`・`slideLayouts/*.xml` を lxml で解析。
3. テーマ参照が出現した場合は `ppt/theme/theme1.xml` の `clrScheme` を辞書化して RGB を決定。
4. サイズや色が `schemeClr` ベースで取得できない場合に備え、`presetClr` や `sysClr` の補完テーブルを用意。
5. 取得した値を `BrandingConfig` にマップし、既存設定との差分を JSON で提示（`--dry-run` で差分のみ確認できるようにする）。

### 実装パターンの比較
- **Option A: 既存 CLI (`uv run pptx ...`) に `pptx branding extract` サブコマンドを追加**
  - *利点*: 設定系コマンドを CLI に統合でき、ブランド設定の更新フローが一元化される。`BrandingConfig` クラスをそのまま流用可能。
  - *懸念*: CLI 依存モジュール（レンダラー、設定ローダー）への依存が増え、抽出専用の軽量スクリプトより起動コストが高い。
  - *実装規模*: 6〜8 時間（CLI 追加、抽出ロジック、単体テスト、統合テスト、ドキュメント更新）。
- **Option B: `scripts/branding_extract.py` のようなスタンドアロン実行ファイル**
  - *利点*: PoC として最小限の依存で実装でき、CLI とは独立して検証を回せる。`uv run` での実行も容易。
  - *懸念*: 後段で CLI に統合する際にエントリーポイントや引数設計を再調整する必要がある。利用者の認知コストが増える。
  - *実装規模*: 4〜6 時間（抽出ロジック、テスト、ドキュメント）。
- **Option C: C#（Open XML SDK）で抽出し、既存仕上げツールに組み込む**
  - *利点*: Open XML SDK の型安全な API でマスター情報を取得でき、サイズ・色の扱いが明確。
  - *懸念*: クロスプラットフォーム動作確認や LibreOffice 連携との差異検証が追加で必要。Python 側とのデータ受け渡しが煩雑。
  - *実装規模*: 10〜12 時間（C# ツール実装、JSON 出力、Python 連携テスト）。

### 推奨方針
- 初期実装は Option B で PoC を構築し、抽出結果の品質を検証した後に Option A へ統合する二段構成が現実的。
- python-pptx API で不足する情報は XML 解析ユーティリティを `src/pptx_generator/settings_extractor.py`（仮称）に切り出し、後続の CLI 実装から再利用できるようにする。
- 抽出結果にはメタ情報（抽出日時、テンプレートファイル名、使用したテーマ ID）を付与し、`docs/policies/config-and-templates.md` でメンテナンス手順をアップデートする必要がある。

### 次のステップ案
1. `templates/` 配下の代表テンプレートを対象に、フォント・カラー・フッターテキストが取得できるか PoC を作成。
2. `BrandingConfig` 用の JSON スキーマ（例: `docs/schemas/branding.schema.json`）を検討し、自動生成値の検証を強化。
3. CLI へ組み込む場合の引数設計（`--template`, `--output`, `--diff-base` など）を整理し、`docs/notes/20251009-template-branding-config.md` に追記する。
