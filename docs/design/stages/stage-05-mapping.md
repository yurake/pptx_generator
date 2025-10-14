# 工程5 マッピング 設計

## 目的
- 承認済みドラフトとテンプレ構造を統合し、レンダリング準備 JSON (`rendering_ready.json`) を生成。
- スコアリング、フォールバック、AI 補完を制御して欠損を最小化する。

## コンポーネント概要
| モジュール | 機能 | 技術 |
| --- | --- | --- |
| Layout Candidate Builder | layout_hint + `layouts.jsonl` から候補を構築 | Python |
| Scoring Engine | 必須充足・容量適合・多様性のスコア計算 | Python, NumPy |
| Assignment Engine | PH ↔ 要素割付、補完の適用 | Python |
| Fallback Controller | 縮約・分割・付録送りのシーケンス制御 | Python |
| Mapping Logger | `mapping_log.json` 出力、監査メタ生成 | Python |

## スコアリング仕様
- 必須充足: PH 必須項目が全て揃っているか（重み 0.5）
- 容量適合: テキスト文字数/表セル数と領域ヒントのマッチ度（重み 0.3）
- 用途タグ: `intent_tag` と layout 用途タグの一致率（重み 0.15）
- 多様性: 直前スライドとのレイアウト重複抑制（重み 0.05）

## 割付アルゴリズム
1. layout_hint がある場合は最優先で候補抽出。  
2. スコアリングで上位 N（既定 3）を取得。  
3. Assignment Engine が PH → 要素を greedy に割付。  
4. 未割付要素があれば AI 補完を起動。  
5. 収容不能なら Fallback Controller が縮約 → 分割 → 付録送りでリトライ。

## AI 補完
- LLM に `elements` と PH 情報を渡し、短縮/再構成を提案。  
- 適用時は `ai_patch` として JSON Patch を保存。  
- 安全チェック（必須項目削除、意図タグ変更は禁止）を通過した場合のみ反映。

## 出力
- `rendering_ready.json`: スライド配列、`layout_id`, `elements[]`, `meta`。
- `mapping_log.json`: 候補スコア一覧、補完箇所、フォールバック履歴、警告。
- `fallback_report.json`（任意）: 失敗スライドの対応指針を列挙。

## エラーハンドリング
- layout_hint 未解決 → `mapping_log` に `error` として記録し exit code 1。
- AI 補完失敗 → 元要素を保持し警告、必要に応じてスライド分割を実行。
- Fallback 全失敗 → 該当スライドを付録へ移し、後工程に警告付きで引き渡す。

## モニタリング
- メトリクス: フォールバック発生率、AI 補完適用率、mapping 所要時間。
- ログ: スコアの生データ、PH 割付結果、AI Patch 詳細。

## テスト方針
- ユニット: スコアリング、割付、フォールバック各モジュールのロジックテスト。
- インテグレーション: サンプル spec を入力し `rendering_ready.json` を検証。
- プロパティテスト: ランダム JSON 生成で不整合を検出。

## 未解決事項
- AI 補完のモデル選定とコスト管理。
- 多様性指標の拡張（ページタイプ分布など）。
- フォールバック結果を HITL に再提示するメカニズム。
