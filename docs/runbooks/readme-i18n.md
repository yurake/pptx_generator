# README 多言語同期ランブック

## 目的
- ルート `README.md`（日本語版）の変更を英語版・中国語版へ迅速に反映する。
- `.locales/translate_readme.py` を用いた自動翻訳と GitHub Actions による差分コミット運用を標準化する。

## 対象
- 日本語: `README.md`
- 英語: `README.en.md`
- 中国語（簡体字）: `README.zh.md`

## 前提条件
- OpenAI API キーを `OPENAI_API_KEY` 環境変数に設定していること。
- 任意: `README_TRANSLATE_MODEL` を設定すると、既定の `gpt-4o-mini` 以外のモデルを利用できる。
- `.locales/translate_readme.py` がリポジトリに存在し、`uv run python` から呼び出せること。
- GitHub Actions では `contents: write` 権限を持つ `GITHUB_TOKEN` を利用可能であること。

## モード概要
| モード | 概要 | 主な利用シーン |
| --- | --- | --- |
| `auto` (既定) | 基準コミットとの差分ブロックのみ翻訳し、既存訳を尊重する。 | Feature ブランチでの通常更新、CI 自動翻訳 |
| `full` | 日本語 README 全体を翻訳して en/zh を再生成する。 | 大規模改訂や構造崩れ発生時の再同期 |

## ローカル手順
1. `uv sync` 等で依存を整える。
2. 必要に応じて `README_TRANSLATE_MODEL` を設定する。
3. 差分更新の場合:
   ```bash
   uv run python .locales/translate_readme.py --mode auto
   ```
   - `--base-ref` 未指定時は自動的に `HEAD^` が比較対象になる。
4. 全文再生成時:
   ```bash
   uv run python .locales/translate_readme.py --mode full
   ```
5. 実行後、`README.en.md` と `README.zh.md` を確認し、必要なら手動で微修正する。
6. `scripts/check_readme_i18n.py` を実装後に併用し、三言語の構造／リンク整合性を検証する。

## GitHub Actions 連携
- ワークフロー例（抜粋）:
  ```yaml
  - name: Translate README
    run: |
      uv run python .locales/translate_readme.py --mode auto --base-ref "${{ github.event.before }}"
  - name: Commit translations
    if: run.steps.translate.outcome == 'success'
    run: |
      git config user.name "github-actions"
      git config user.email "github-actions@users.noreply.github.com"
      git add README.en.md README.zh.md
      if ! git diff --cached --quiet; then
        git commit -m "chore(readme): sync translations"
        git push
      fi
  ```
- 条件:
  - 同一プッシュで `README.md`・`README.en.md`・`README.zh.md` がすべて更新済みの場合、スクリプトが翻訳処理をスキップし既存差分を尊重する。
  - エラー発生時はジョブを失敗扱いにし、手動対応する。

## 運用上の注意
- Language switcher のリンクは 3 ファイルで同一構造に保つ。
- 翻訳結果に違和感がある場合は該当ブロックのみ手動修正し、次回 `auto` 実行時に上書きされないよう差分を維持する。
- API 失敗で一部ブロックが未翻訳の場合、スクリプトは既存訳を保持して警告を表示する。ログを確認し再実行すること。

## トラブルシュート
| 症状 | 原因候補 | 対応 |
| --- | --- | --- |
| en/zh のブロック数がずれる | 手動編集で構造変更 | `--mode full` で再生成後、必要な手修正を行う |
| LLM API エラー | ネットワーク／レートリミット | 待機後に再実行。過剰失敗時は手動翻訳も検討 |
| CI で push 失敗 | `GITHUB_TOKEN` 権限不足 | ワークフローの `permissions` を `contents: write` に設定 |
| 翻訳が上書きされない | 三言語すべて変更済み | 仕様通りスキップ。不要なら手動編集のみで完結させる |

## 今後の拡張候補
- `scripts/check_readme_i18n.py` による構造検証を CI に組み込み、差分漏れを早期検知する。
- 用語集ファイルを導入し、翻訳スタイルの統一を強化する。
