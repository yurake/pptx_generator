# アーキテクチャ設計メモ（横断）

- 役割: stage をまたぐ設計方針・共通ガバナンスをまとめる置き場。機能別・非機能別ではなく、パイプライン横断のテーマを集約する。
- 読み順: 必要なテーマのみ参照し、詳細は各ファイルへ。stage 固有の補足は `docs/design/stages/` で管理する。

## 横断テーマ
| テーマ | 適用 stage | 内容 |
| --- | --- | --- |
| [テンプレートスタイルガバナンス](./template-style-governance.md) | S1 / S3 / S4 | レイアウト別スタイル設定と `branding.json` スキーマの設計。 |
| [静的テンプレ Blueprint](./template-blueprint.md) | S2 / S3 | 静的テンプレの Blueprint 定義と slot 充足設計。 |

## stage 補足（関連）
- `docs/design/stages/stage-01-jobspec-catalog.md`: S1 の jobspec 抽出設計メモ。
- `docs/design/stages/stage-03-story-modeler.md`: S3 のストーリー骨子連携メモ。
