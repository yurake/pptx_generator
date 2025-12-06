# Blueprint 静的データ拡張メモ (2025-12-06)

## 背景
- Blueprint に `default_text` は追加済みだが、表やチャートなど構造化データを保持していない。
- 静的テンプレートの Stage3 でカードが欠落しても既定値で埋め戻したい。
- Stage4 では外部フックに依存せず標準レンダラーで完結させたい。

## 静的テンプレート棚卸し
- 現在 Blueprint に `default_text` を保持しているテンプレ:
  - `templates/sample.pptx`（`.pptx/jri` セットを使用）
- 今後確認すべき候補:
  - `templates/jri_template.pptx`
  - `templates/jri_template2.pptx`
  - `templates/agent_discussion_20251030.pptx`
- フック構成:
  - `external/sample/hooks.json` は Stage4 フックを `null` 済み。
  - `external/sample_bk/hooks.json`、`external/demo_tpl/hooks.json` は従来構成のため、Blueprint 拡張導入時に再整理が必要。

## 想定タスク
1. Stage1 で表・チャートの抽出 PoC（`python-pptx` からセル/系列情報を取得できるか確認）。
2. Blueprint スキーマに `default_payload` を追加し、表データを JSON 化するルールを決定。
3. Stage3 でカード未割当スロットに `default_payload` をマージする処理を追加。
4. Stage4 標準レンダラーで表・チャートを復元できるようテーブル描画ロジックを拡張。
5. ドキュメント更新（`docs/design/stages/stage-01-template.md`, `docs/design/stages/stage-04-gen.md` 等）。

## 留意点
- テンプレによって表構造（列数・見出し）が異なるため、Blueprint へ格納する際の正規化ルールが必要。
- 既存の Stage3 ログ（`mapping_log.json`）に既定値適用が分かるフラグを追加する。
- generate_ready の差分が大きくなるため、`inspect_static_pptx.py` など検証ツールを併せて更新する。

## 次のステップ
- RM-088（テンプレ実スライド優先抽出）と連携し、実スライドをソースに Blueprint を生成できるようにする。
- フォールバック適用時の監査ログ設計を検討し、静的モードでも差分確認が容易な状態を整える。
