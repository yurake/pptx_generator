# README バッジ整備メモ（2025-11-23）

RM-074 に向けた要望を整理する。

## 目的
- `sonarcloud.io` を導入し、静的解析結果をバッジとして README に表示できるようにする。
- 以下の例を参考に、主要バッジを README に追加する。

## 現状整理（2025-11-24）
- README にはバッジが未掲載で、ロゴ画像と概要説明から始まっている。冒頭へ任意の Markdown を挿入するスペースは十分にある。
- CI は `.github/workflows/ci.yml` の単一ジョブで `uv run --extra dev pytest` と Polisher .NET テストを実行している。ここに SonarCloud ステップを追加する。
- Secrets 前提で実行するため `SONAR_TOKEN`（SonarCloud で生成）と既存の `GITHUB_TOKEN` を利用する。Secrets 未設定時のフォールバックは設けない。

## 追加したいバッジと参考例
- **License バッジ**: 例）<https://github.com/langchain-ai/langchain/blob/master/README.md>
- **GitHub Actions（CI）バッジ**: 例）<https://github.com/google/adk-python/blob/main/README.md>
- **Python バージョンバッジ**: 例）<https://github.com/HKUDS/LightRAG/blob/main/README.md>
- **SonarCloud バッジ**: 新規にプロジェクトをセットアップし、品質ゲート／カバレッジ等を取得する。取得可能なメトリクスは全て README に掲載する。

### SonarCloud バッジ候補（project = `pptx_generator`, org = `yurake` を想定）
| メトリクス | バッジ URL（例） |
| --- | --- |
| Quality Gate | `https://img.shields.io/sonar/quality_gate/yurake_pptx_generator?server=https%3A%2F%2Fsonarcloud.io` |
| Coverage | `https://img.shields.io/sonar/coverage/yurake_pptx_generator?server=https%3A%2F%2Fsonarcloud.io` |
| Bugs | `https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&metric=bugs` |
| Vulnerabilities | `https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&metric=vulnerabilities` |
| Code Smells | `https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&metric=code_smells` |
| Maintainability Rating | `https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&metric=sqale_rating` |
| Reliability Rating | `https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&metric=reliability_rating` |
| Security Rating | `https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&metric=security_rating` |
| Duplicated Lines Density | `https://sonarcloud.io/api/project_badges/measure?project=yurake_pptx_generator&metric=duplicated_lines_density` |

※ プロジェクトキー／組織は SonarCloud 登録時に確定させ、README と CI の設定値が一致するようにする。

## 検討事項
- README へのバッジ追加（英語版・中国語版 README への展開を含む運用整備）。
- SonarCloud のプロジェクト設定、トークン管理、CI 連携。
- 既存 GitHub Actions ワークフローへの組み込みとバッジ URL の決定。

## 次アクション
1. `sonar-project.properties` を作成し、`sonar.organization=yurake`、`sonar.projectKey=yurake_pptx_generator` などを定義する。
2. `.github/workflows/ci.yml` に SonarCloud ステップを追加し、Python/Node キャッシュは `uv` で管理する。
3. README 冒頭でバッジをセンタリング表示し、4 言語展開を想定した更新ルールを追記する。
