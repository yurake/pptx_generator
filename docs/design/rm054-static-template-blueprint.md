# RM-054 静的テンプレ Blueprint 設計メモ

## 背景
- 静的テンプレートではスライド順・slot が固定されるため、工程2・工程3 で Blueprint を共通参照し、HITL が差戻し判断を行う際に slot 充足状況を把握できるようにする。
- `template_spec.json` に Blueprint を追加し、`pptx prepare` と `pptx compose` 系コマンドで一貫して扱う。

## Blueprint スキーマ概要
```jsonc
{
  "layout_mode": "static",
  "blueprint": {
    "slides": [
      {
        "slide_id": "cover",
        "layout": "Title",
        "intent_tags": ["opening"],
        "required": true,
        "slots": [
          {
            "slot_id": "cover.title",
            "anchor": "Title",
            "content_type": "text",
            "required": true,
            "intent_tags": ["headline"]
          },
          {
            "slot_id": "cover.subtitle",
            "anchor": "Sub Title",
            "content_type": "text",
            "required": false
          }
        ]
      }
    ]
  }
}
```

- `slide_id`: 工程2・工程3 で共通利用する論理スライド ID。
- `slots[*]`: slot 単位でコンテンツ種別とアンカー名を定義。`required=true` の slot は必須充足対象。
- `intent_tags`: AI 呼び出し時のプロンプト補助・工程3 でのマッピングヒントとして利用する。
- `required`（slide レベル）: 付録や任意スライドの扱いを明示する。`false` の場合は未生成でもエラー扱いしない。

## 工程2（`pptx prepare`）連携
- CLI は `--mode` を必須化し、`static` 選択時は `--template-spec` を受け取る。
- Blueprint の slot を順番に巡回し、slot ごとにカードを生成。必要に応じて AI プロンプトに `slot_id` / `anchor` / `intent_tags` を付加する。
- 生成カードには以下の追加メタを付与する。
  - `slide_id`: Blueprint スライドと一致させる。
  - `slot_id`: Blueprint slot と一致させる。
  - `layout_mode`: `static` 固定。
  - `required`: slot の必須フラグ、工程3 での検証用。
  - `blueprint_slot`: Blueprint 情報をそのまま埋め込み、後工程で参照できるようにする。
- 必須 slot へカードが生成できなかった場合は exit code 6 を返し、`slot_validation.errors` を標準エラーへ出力する。
- `ai_generation_meta.json` に `blueprint_path`（絶対パス）と `blueprint_hash`（SHA256）、`slot_coverage`（必須/任意の充足統計）を記録する。

## 工程3（`draft_structuring` / `mapping`）連携
- `ai_generation_meta.mode` と `ai_generation_meta.blueprint_path` を受け取り、静的モード時は以下の分岐を行う。
  - レイアウトスコアリング・フォールバックをスキップし、カード→slot マッピングを検証。
  - 未充足の必須 slot は `DraftStructuringError` を送出し、差戻し推奨として `draft_mapping_log.json.static_slot_checks` に記録する。
  - Blueprint に定義されていないカードは `orphan_cards` として警告し、採用可否を CLI オプションで制御（初期実装では警告のみ）。
- `generate_ready.json` の `slides[*].meta` へ Blueprint 情報を転記し、レンダリング工程で slot を参照できるようにする。
- `generate_ready.slides[*].meta.blueprint_slots[*].fulfilled` を保持し、工程4 の監査とレンダリングで slot 充足状況を再利用する。
- 監査ログ (`draft_mapping_log.json`, `generate_ready_meta.json`) に `layout_mode=static` と slot 充足統計を残し、`static_slot_checks` に未充足 slot / orphan cards を記録する。

## レンダリング工程への影響
- `generate_ready.json.meta.layout_mode` を参照し、静的モード時はレンダリング監査で必須 slot 未充足が 0 件であることを確認する。
- Blueprint slot のアンカー名をそのまま利用するため、テンプレ側の shape 名と齟齬がある場合はテンプレ工程の検証で弾く。

## 監査・運用メモ
- Blueprint ファイルのハッシュは工程2・工程3 の監査ログに記録し、将来の改版時に差分追跡できるようにする。
- `docs/policies/config-and-templates.md` に静的テンプレ投入手順と Blueprint 更新手続き（承認フロー）を追記予定。
- 既存の動的モードは後方互換を維持し、Blueprint 未指定時は従来どおりレイアウト探索を行う。
