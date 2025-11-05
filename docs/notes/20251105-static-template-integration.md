# 静的テンプレート対応検討メモ（2025-11-05）

- 背景: 静的テンプレート（スライド順・プレースホルダが固定）を現行の動的テンプレート中心パイプラインへ統合する方針を整理。ロードマップの新規項目 RM-054 として管理する。
- 現状（動的モード）: 工程2 `pptx prepare` はテンプレ参照なしで BriefCard を生成し、工程3 `pptx compose` がレイアウトスコアリングとフォールバックで最適レイアウトを決定している。
- 静的モード要件: テンプレ Blueprint（slide_id / slot_id / 意図タグ / 必須フラグ）を前提に、工程2でカードを slot 単位に生成し、工程3では空き slot の検知と監査が中心となる。マッピング候補の探索は不要。
- 工程1への追加: `template_spec` に `layout_mode: dynamic|static` と静的テンプレ用 Blueprint を追加。テンプレ抽出 CLI は Blueprint を生成し、テンプレ版ごとの固定スライド構成を提供する。
- 工程2の拡張:
  - CLI オプションで Blueprint を指定 (`--template-spec` など) し、生成 AI が slot 情報を参照してテキストを構成。
  - `prepare_card.json` に `slot_id`、`slide_id`、必須/任意の充足ステータス、`layout_mode` を追加。
  - `ai_generation_meta.json` に必須 slot 充足率や Blueprint 参照情報を記録し、監査ログへ連携する。
- 工程3の分岐:
  - 動的モード: 現行どおりレイアウトスコアリング・フォールバック・`generate_ready` 生成を担当。
  - 静的モード: Blueprint をベースに `draft_approved.json` を検証し、空き slot や未使用カードをログ化。`generate_ready.json` は工程2成果物をバリデーション後に確定する。フォールバックは「slot 未充足 → 差戻し」中心へ見直す。
  - `mapping_log.json` に `mode=static` の監査項目（必須 slot 空き件数、差戻し推奨理由）を追加。
- 工程4の補足: 静的モード時は `generate_ready` に `layout_mode=static` を保持し、レンダリング監査で必須 slot 空きが 0 件であることを品質ゲート化。
- 未決定事項:
  - Blueprint スキーマの詳細（入れ子構造、付録扱い）とテンプレ差分管理方法。
  - 静的テンプレ専用の差戻し理由セットや UI 連携方法。
  - 動的・静的モードの CLI UX（自動判定 vs オプション指定）の最終方針。
- 次アクション: Blueprint スキーマ案と CLI 拡張仕様を起票し、工程2/3 のスキーマ変更案を `docs/requirements/` と `docs/design/` へ落とし込む。関連タスクを細分化して RM-054 の ToDo へ展開する。
