# 工程3 マッピング (HITL + 自動) 設計

## 目的
- Brief 成果物とテンプレ構造を突合し、章構成承認（HITL）とレイアウト割付（自動）を一体化する。
- `draft_approved.json` と `rendering_ready.json` を同時に更新し、監査しやすいログ (`draft_review_log.json`, `mapping_log.json`) を残す。
- 再実行や差戻しが発生した際もディレクトリ構造を固定し、CLI／自動化からの運用を容易にする。

## コンポーネント
| コンポーネント | 役割 | 技術 | 備考 |
| --- | --- | --- | --- |
| Draft Engine | 章構成・差戻しワークフロー | Python / dataclass | `draft_*` ファイルとテンプレ適合率を管理 |
| Layout Hint Engine | レイアウト候補スコアリング | Python | Brief の intent / chapter / Analyzer 指摘を参照 |
| Mapping Engine | プレースホルダ割付・フォールバック制御 | Python | `rendering_ready.json`, `mapping_log.json` を生成 |
| CLI | `pptx compose` / `pptx outline` / `pptx mapping` | Click | compose が工程3全体をラップ |

## 入出力
- 入力: `jobspec.json`, `layouts.jsonl`, `brief_cards.json`, `brief_log.json`, `ai_generation_meta.json`,（任意）`analysis_summary.json`。
- 出力: `draft_draft.json`, `draft_approved.json`, `draft_meta.json`, `draft_review_log.json`, `rendering_ready.json`, `mapping_log.json`, `fallback_report.json`。

## ワークフロー概要
1. `pptx compose` が Brief 成果物を読み込み、章テンプレート辞書 (`config/chapter_templates/`) に基づいて初期章構成を作成。
2. HITL が `draft_draft.json` を確認し、章順・付録・差戻し理由を調整。`--show-layout-reasons` でレイアウト候補の理由を確認可能。
3. 章承認が完了すると Draft Engine が `draft_approved.json` を確定し、Mapping Engine へバトンを渡す。
4. Mapping Engine はレイアウト候補とテンプレ構造を突合し、プレースホルダ割付を実行。必要に応じてフォールバック（縮約→分割→付録送り）を適用し履歴を `mapping_log.json` へ記録。
5. `rendering_ready.json`／`mapping_log.json` が生成され、監査ログにハッシュと統計が追加される。

## CLI
### `pptx compose`
- 主なオプション
  | オプション | 説明 | 既定値 |
  | --- | --- | --- |
  | `<jobspec.json>` | Stage1 で抽出したジョブスペック | 必須 |
  | `--brief-cards <path>` | 工程2の BriefCard | `.brief/brief_cards.json` |
  | `--brief-log <path>` | 工程2のレビュー ログ | `.brief/brief_log.json` |
  | `--brief-meta <path>` | 工程2の生成メタ | `.brief/ai_generation_meta.json` |
  | `--draft-output <dir>` | ドラフト成果物のディレクトリ | `.pptx/draft` |
  | `--output <dir>` | マッピング成果物のディレクトリ | `.pptx/gen` |
  | `--layouts <path>` | テンプレ構造 (`layouts.jsonl`) | 任意 |
  | `--template <path>` | ブランド抽出用テンプレート | 任意 |
  | `--rules <path>` | マッピングルール設定 | `config/rules.json` |
  | `--show-layout-reasons` | レイアウト候補のスコア内訳を表示 | 無効 |

- ドラフト関連の追加オプション: `--target-length`, `--structure-pattern`, `--appendix-limit`, `--chapter-template` など。詳細は CLI リファレンスを参照。

### `pptx outline`
- ドラフト構成のみを再実行する際に利用。`--brief-*` オプションは `compose` と共通。
- 差戻し後に Draft のみ更新したいケースや UI 連携での個別更新時に利用する。

### `pptx mapping`
- レイアウト割付のみ再実行する際に利用。既存の `draft_approved.json` と Brief 成果物を入力として受け付ける。
- `--brief-*`, `--layouts`, `--rules` など `compose` と同じオプションを持ち、`rendering_ready.json` と `mapping_log.json` を更新する。

## ログ・監査
- `draft_review_log.json`: 章/スライドの承認・差戻し履歴（`action`, `actor`, `timestamp`, `reason_code`, `notes`）。
- `mapping_log.json`: レイアウト候補スコア、AI 補完、フォールバック履歴、Analyzer サマリ。
- `fallback_report.json`: 重大フォールバックの詳細（適用戦略、対象スライド、理由）。
- 監査ログ (`audit_log.json`) にはドラフト・マッピングのハッシュと発生件数を記録する。

## Analyzer 連携
- 工程4の `analysis.json` を `--import-analysis` で読み込み、章構成ポリシーの調整や差戻し判断に活用。
- Analyzer 指摘件数が閾値を超える場合はレイアウト候補の優先順位を下げる。

## 未解決事項
- 章テンプレと BriefCard の自動突合ロジックの高度化。
- レイアウト候補スコアの ML 化と継続学習。
- `mapping_log.json` のダイジェスト表示（CLI/監視ダッシュボード）実装。
- Analyzer 指摘を踏まえた自動フォールバック戦略のチューニング。
