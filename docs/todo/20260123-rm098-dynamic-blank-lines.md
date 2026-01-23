# RM-098 Dynamicモード空行保持機能実装

## 📋 概要

**目的**: RM-098の空行保持機能をDynamicモードでも機能させる

**課題**: Staticモードでは空行が保持されるが、Dynamicモードでは空行が削除され`buNone`エラーが発生する

**原因**: Prepare AIが原稿を要約する際、箇条書き内の空行を不要な改行として削除してしまう

**解決策**: Prepare AIプロンプトに空行保持の指示を追加

---

## 🎯 実装内容

### 修正ファイル

**[`src/pptx_generator/prepare_ai/prompts.py`](../../src/pptx_generator/prepare_ai/prompts.py)**

### 変更内容

#### 1. Dynamicモードプロンプトへの追加

- **導入部への追加**（7-8行目）:
  ```python
  **重要**: 箇条書き内の空行は、読みやすさのために意図的に配置されています。
  body配列のbulletsブロック内で空行を保持する場合は、items配列に `{"text": "", "level": 0}` を挿入してください。
  ```

- **bulletsフォーマット説明への追加**（23行目）:
  ```python
  **空行を保持する場合は `{"text": "", "level": 0}` を挿入する**
  ```

#### 2. Staticモードプロンプトへの追加

- **導入部への追加**（40-41行目）:
  ```python
  **重要**: 箇条書き内の空行は、読みやすさのために意図的に配置されています。
  body配列のbulletsブロック内で空行を保持する場合は、items配列に `{"text": "", "level": 0}` を挿入してください。
  ```

- **bulletsフォーマット説明への追加**（56行目）:
  ```python
  **空行を保持する場合は `{"text": "", "level": 0}` を挿入する**
  ```

---

## 📊 期待される効果

### 修正前の出力例
```json
{
  "body": [
    {
      "type": "bullets",
      "items": [
        {"text": "項目A", "level": 0},
        {"text": "項目B", "level": 0}
      ]
    }
  ]
}
```

### 修正後の出力例
```json
{
  "body": [
    {
      "type": "bullets",
      "items": [
        {"text": "項目A", "level": 0},
        {"text": "", "level": 0},
        {"text": "項目B", "level": 0}
      ]
    }
  ]
}
```

---

## ⚠️ リスク評価

| 項目 | レベル | 理由 | 対策 |
|------|--------|------|------|
| 既存機能への影響 | 低 | プロンプト追加のみで既存ロジックは変更なし | - |
| LLM依存性 | 中 | LLMが指示を正しく解釈する前提 | テストで検証 |
| 後方互換性 | 高 | 空行なしのケースでも問題なく動作 | 既存テスト実行 |

---

## ✅ テスト計画

### 1. ユニットテスト
- [ ] 空行を含むMarkdown入力でPrepare AI呼び出し
- [ ] `prepare_card.json`に空行が`{"text": "", "level": 0}`として保持されることを確認
- [ ] 空行なしの入力でも正常に動作することを確認

### 2. 統合テスト（Dynamic全ステージ）
- [ ] `prepare`ステージ: `prepare_card.json`に空行が保持される
- [ ] `structure`ステージ: `generate_ready.json`に空行が引き継がれる
- [ ] `generate`ステージ: PPTX生成時に`buNone`エラーが発生しない
- [ ] 生成されたPPTXで箇条書き内の空行が視覚的に確認できる

### 3. 回帰テスト
- [ ] 既存のStaticモードテストが全てパス
- [ ] 既存のDynamicモードテスト（空行なし）が全てパス

---

## 📝 作業履歴

### 2026-01-23
- [x] 最新upstream/mainを取得
- [x] ブランチ作成: `feat/rm098-dynamic-blank-lines`
- [x] [`prompts.py`](../../src/pptx_generator/prepare_ai/prompts.py)にDynamicモード用の空行保持指示を追加
- [x] [`prompts.py`](../../src/pptx_generator/prepare_ai/prompts.py)にStaticモード用の空行保持指示を追加
- [x] ToDoファイル作成
- [ ] 変更をコミット
- [ ] テストケース追加
- [ ] 動作確認
- [ ] Issue起票
- [ ] PR作成

---

## 🔗 関連情報

### 関連Issue
- RM-098: 空行保持機能の元Issue（Staticモードでの実装）
- 新規Issue: Dynamicモードでの空行保持（起票予定）

### 関連ファイル
- [`src/pptx_generator/prepare_ai/prompts.py`](../../src/pptx_generator/prepare_ai/prompts.py) - 修正対象
- [`src/pptx_generator/prepare_ai/client.py`](../../src/pptx_generator/prepare_ai/client.py) - Prepare AI呼び出し
- `tests/prepare_ai/` - テスト追加予定

### 参考
- [会話ログ](../qa/20260123-clinetalk.md) - Clineとの会話記録

---

## 🚀 次のステップ

1. **即座に実施**
   - [ ] 変更をコミット
   - [ ] テストケース作成

2. **動作確認後**
   - [ ] Issue起票（yurake/pptx_generator）
   - [ ] PR作成

3. **マージ後**
   - [ ] ドキュメント更新
   - [ ] チームへの共有

---

## 📅 ステータス

- **作成日**: 2026-01-23
- **最終更新**: 2026-01-23
- **担当**: @kkeito-investigate
- **ステータス**: 🚧 実装中
- **ブランチ**: `feat/rm098-dynamic-blank-lines`
- **ベース**: `upstream/main` (eeb0489)