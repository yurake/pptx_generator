# 工程1 テンプレ準備 設計

## 目的とスコープ
- ブランドごとのテンプレ資産を安定して提供し、後続工程が追加メタ無しで利用できる状態を作る。
- テンプレ構築は PowerPoint 操作（人手）が主体だが、品質担保と受け渡しは自動化を前提に設計する。

## アーキテクチャ構成
| モジュール | 役割 | 主な技術 / ツール |
| --- | --- | --- |
| Template Authoring | PPTX 編集・レイアウト設計 | PowerPoint, Figma（参考） |
| Template Release CLI | `template_release.json` 生成、差分チェック起動 | Python, `python-pptx`, Click |
| Golden Sample Runner | 代表 spec / レンダリングジョブの実行 | `uv run pptx gen`, LibreOffice |

## フロー詳細
1. **テンプレ編集**  
   - 作業結果を `templates/libraries/<brand>/<version>/template.pptx` に保存。  
   - PH 命名規約（`PH__<Role>__<Index>`）とレイアウト命名規約を遵守。
2. **自動診断 (仮)**  
   - Template Release CLI がテンプレを解析し、`template_release.json` と差分レポートを生成。  
   - 重複 PH / 不正レイアウトがあれば `release_report.json` に出力し FAIL。
3. **互換性チェック**  
   - Golden Sample Runner が既知 spec を用いてレンダリング → Analyzer → LibreOffice まで通し、互換性指標を算出。  
   - エラー時は差分レポートにハッシュとログパスを記録。
4. **アーカイブ**  
   - Release CLI が成果物（PPTX, release.json, diagnostics）を `templates/releases/<brand>/<version>/` にまとめる。

## インターフェース
- CLI: `uv run tools/template_release create --template templates/.../template.pptx --brand <brand> --version <version>`
- 成果物: `template_release.json`, `release_report.json`, `golden_runs/*.log`
- CI Hook (予定): PR 時に CLI を実行し、失敗時はレビューをブロック。

## 監視・ログ
- Release CLI: 生成時刻、操作者、テンプレパス、検出エラーを構造化ログに記録。
- Golden Sample: 成功/失敗、LibreOffice exit code、差分件数。

## テスト方針
- CLI 単体テスト: release JSON スキーマ、差分出力、失敗時の exit code。
- 統合テスト: サンプルテンプレを用いた end-to-end リリース（PPTX → release → sample render）。

## 未解決事項 / TODO
- テンプレ差分検出アルゴリズム（図形比較 VS JSON 差分）の詳細設計。
- ゴールデンサンプルの自動生成と削除ポリシー。
- LibreOffice / Open XML Polisher のバージョン固定戦略。

## 関連スキーマ
- [docs/design/schema/stage-01-template-preparation.md](../schema/stage-01-template-preparation.md)
- サンプル: `docs/design/schema/samples/template_release.jsonc`（準備予定）
