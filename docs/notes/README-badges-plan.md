# README バッジ整備メモ（2025-11-23）

RM-073 に向けた要望を整理する。

## 目的
- `sonarcloud.io` を導入し、静的解析結果をバッジとして README に表示できるようにする。
- 以下の例を参考に、主要バッジを README に追加する。

## 追加したいバッジと参考例
- **License バッジ**: 例）<https://github.com/langchain-ai/langchain/blob/master/README.md>
- **GitHub Actions（CI）バッジ**: 例）<https://github.com/google/adk-python/blob/main/README.md>
- **Python バージョンバッジ**: 例）<https://github.com/HKUDS/LightRAG/blob/main/README.md>
- **SonarCloud バッジ**: 新規にプロジェクトをセットアップし、品質ゲート／カバレッジ等を取得する。

## 検討事項
- README へのバッジ追加（英語版・中国語版 README への展開を含む運用整備）。
- SonarCloud のプロジェクト設定、トークン管理、CI 連携。
- 既存 GitHub Actions ワークフローへの組み込みとバッジ URL の決定。
