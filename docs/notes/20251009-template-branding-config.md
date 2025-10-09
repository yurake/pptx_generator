## PPTX テンプレートから branding.json 自動生成の調査（2025-10-09）

### 調査の狙い
- テンプレート更新とブランド設定 JSON の乖離を防ぎ、スタイル管理を効率化する仕組みの成立可否を確認する。
- `config/branding.json` が要求する項目（フォント、カラー、フッター）をテンプレートからどこまで抽出できるかを把握する。

### 抽出対象とテンプレート側の情報源
- フォント名・スタイル:
  - スライドマスターの `theme/fontScheme` に Heading / Body のフォントファミリが格納される。
  - python-pptx では `presentation.part.theme` から `font_scheme.major_font / minor_font` を参照できるが、サイズ情報は保持していない。
- フォントサイズ・装飾:
  - プレースホルダーに残っている段落の `rPr` から取得可能。ただしテンプレートが空文字の場合は情報を持たない。
  - Open XML SDK や直接 XML 解析で `defRPr`（既定段落プロパティ）を読むと、既定サイズや色を取得できる。
- カラーパレット:
  - `theme/colorScheme` に accent1〜accent6、dark/light 系の色がある。
  - python-pptx で `presentation.slide_master.theme_color_scheme` を通じて RGB を参照できる。
  - `config/branding.json` の primary / secondary / accent / background へマッピングルールを定義する必要がある。
- フッター文言:
  - 多くの場合テンプレート内に静的テキストで埋め込まれる。スライドマスターのフッタープレースホルダー `sldMaster/spTree/` から抽出が必要。
  - python-pptx はフッター API を持つが、マスターのテキスト取得は限定的で XML 直接読み込みが確実。

### 利用を想定する技術要素
- python-pptx によるテンプレート読み込みとスライドマスター / テーマ情報の抽出。
- `pptx.oxml` 経由で `ppt/theme/theme1.xml` や `ppt/slideMasters/slideMaster1.xml` をパースし、フォントサイズ・配色・フッターの既定値を取得。
- LibreOffice（headless）を併用し、テンプレート内のスタイル一覧出力（例: `soffice --headless --convert-to` では情報不足のため、マクロや XML 抽出の補助ツールとして検討）。
- Open XML SDK ベースの既存仕上げツールを流用し、テンプレートからテーマ情報を抽出する C# スクリプトを CLI から呼び出す案。

### 想定される変換フロー案
1. CLI でテンプレートパスを受け取り、python-pptx でプレゼンテーションをロード。
2. テーマ（フォント・カラー）を抽出し、ブランド設定項目へマッピング。
3. スライドマスター XML を解析して、既定段落プロパティからサイズ・色を補完。
4. 取得できない項目（例: primary/secondary の優先順位、アクセント → accent）についてはヒューリスティックまたは対話式確認を行う。
5. 生成した設定を `branding.json` テンプレートへ書き出し、ユーザーが微調整できるよう差分出力を併せて提示。

### 課題とリスク
- python-pptx が既定段落スタイルのサイズを直接提供しないため、XML 解析または別ツール連携が必須。
- テンプレートによってはテーマカラーの割り当てがブランド色と一致しておらず、適切なマッピングルールが必要。
- フッターや補足情報がスライドごとに異なる場合、自動抽出で一意の値を決められない可能性がある。
- LibreOffice や Open XML SDK を組み合わせる場合、実行環境の依存が増える。

### 次のアクション候補
- python-pptx と XML 解析を併用した PoC スクリプトの作成。
- `branding.json` スキーマにテンプレート由来のメタ情報（抽出元など）を付与する拡張案を検討。
- 代表的なテンプレート（`templates/` 配下）で抽出精度を検証し、ヒューリスティックが妥当か評価。
- CLI コマンド追加時のインターフェース設計（テンプレート → JSON、差分出力、既存 config へのマージ戦略）を整理。
