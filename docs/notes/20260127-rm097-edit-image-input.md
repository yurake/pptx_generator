# RM-097 Stage5 edit 画像入力メモ

## 目的
- Stage5 edit の指示抽出でスライドスクリーンショットを利用できるようにする。
- shape_id と座標情報を併用し、画像とテキストの対応を取りやすくする。

## 有効化
- 環境変数 `PPTX_EDIT_IMAGE_INPUT=1` で画像入力を有効化する。
- 未指定の場合は従来どおりテキストのみで指示抽出を行う。

## 画像生成
- LibreOffice (soffice) で PPTX を画像化する。
- 画像形式は `PPTX_EDIT_IMAGE_FORMATS` (例: `png,jpg`) で指定する。
- `PPTX_EDIT_IMAGE_PREFER_FIRST=1` の場合、最初に成功した形式のみを採用する。
- 画像形式の優先順は `PPTX_EDIT_IMAGE_FORMAT_ORDER` で指定する。
- タイムアウトとリトライは `PPTX_EDIT_IMAGE_TIMEOUT_SEC` / `PPTX_EDIT_IMAGE_RETRIES` で指定する。
- 出力先は edit の出力ディレクトリ配下 `images/`。
  - 例: `<output_dir>/images/png/slide_001.png`
- LibreOffice パスは `PPTX_EDIT_IMAGE_SOFFICE_PATH` または `LIBREOFFICE_PATH` で指定できる。

## メタ情報
- `images/edit_slide_images.json` に以下を記録する。
  - PPTX パス、スライドサイズ、スライドごとの画像一覧
  - shape_id と座標（left/top/width/height）などの幾何情報

## LLM への入力
- 画像が有効な場合は、画像とメタ情報を LLM 入力に付与する。
- 画像が無効な場合はテキストのみで従来の挙動を維持する。
