# UAT: 空行保持機能の動作確認

## 目的
RM-098のDynamicモード空行保持機能が実際のLLMで正しく動作することを確認する。

## テストケース

### TC-1: Dynamicモードでの空行保持（基本）

#### 前提条件
- LLM Provider設定済み（OpenAI/AWS Claude）
- `.env`ファイルに認証情報設定済み

#### テスト手順

1. **テスト用Markdown作成**
```bash
cd pptx_generator
cat > .pptx/uat/blank_lines_input.md << 'EOF'
# サービス紹介

## 概要
- 主要機能A
- 主要機能B

- 対象顧客

## 課題
- 現状の問題点A

- 現状の問題点B

- 現状の問題点C

## 解決策
- 提案1：システム導入

- 提案2：プロセス改善

- 提案3：人材育成
EOF
```

2. **Prepare実行（Dynamic Mode）**
```bash
mkdir -p .pptx/uat
uv run pptx prepare .pptx/uat/blank_lines_input.md --mode dynamic
```

3. **prepare_card.json確認**
```bash
cat .pptx/prepare/prepare_card.json | jq '.cards[].content.body[] | select(.type=="bullets") | .items'
```

#### 期待結果
- `prepare_card.json`のbulletsブロック内に空行が`{"text": "", "level": 0}`として保持されている
- 例:
```json
{
  "type": "bullets",
  "items": [
    {"text": "主要機能A", "level": 0},
    {"text": "主要機能B", "level": 0},
    {"text": "", "level": 0},
    {"text": "対象顧客", "level": 0}
  ]
}
```

---

### TC-2: 全ステージでの空行保持確認

#### テスト手順

1. **Templateステージ（前提）**
```bash
uv run pptx template samples/templates/dynamic_template.pptx --mode dynamic
```

2. **Composeステージ**
```bash
uv run pptx compose .pptx/template/jobspec.json --prepare-cards .pptx/prepare/prepare_card.json
```

3. **generate_ready.json確認**
```bash
cat .pptx/compose/generate_ready.json | jq '.slides[].elements[] | select(.type=="bullets") | .items'
```

4. **Generateステージ**
```bash
uv run pptx gen .pptx/compose/generate_ready.json
```

5. **生成されたPPTX確認**
- `.pptx/gen/proposal.pptx`を開く
- 箇条書きスライドで空行が視覚的に確認できるか

#### 期待結果
- `generate_ready.json`でも空行が保持されている
- 生成されたPPTXファイルで箇条書き内の空行が視覚的に確認できる
- `buNone`エラーが発生しない

---

### TC-3: 空行なしのケース（回帰テスト）

#### テスト手順

1. **空行なしMarkdown作成**
```bash
cat > .pptx/uat/no_blank_lines_input.md << 'EOF'
# サービス紹介

## 概要
- 主要機能A
- 主要機能B
- 対象顧客

## 課題
- 現状の問題点A
- 現状の問題点B
- 現状の問題点C
EOF
```

2. **Prepare実行**
```bash
uv run pptx prepare .pptx/uat/no_blank_lines_input.md --mode dynamic
```

3. **結果確認**
```bash
cat .pptx/prepare/prepare_card.json | jq '.cards[].content.body[] | select(.type=="bullets") | .items'
```

#### 期待結果
- 空行なしでも正常に処理される
- itemsに空文字列のtext要素が含まれない
- 既存機能が壊れていないことを確認

---

### TC-4: 階層付き箇条書きでの空行保持

#### テスト手順

1. **階層付きMarkdown作成**
```bash
cat > .pptx/uat/nested_blank_lines_input.md << 'EOF'
# プロジェクト計画

## フェーズ1
- 要件定義
  - ヒアリング実施
  - 要件書作成

- 設計
  - 基本設計
  - 詳細設計

## フェーズ2
- 開発
  - 実装
  - 単体テスト

- テスト
EOF
```

2. **Prepare実行**
```bash
uv run pptx prepare .pptx/uat/nested_blank_lines_input.md --mode dynamic
```

3. **結果確認**
```bash
cat .pptx/prepare/prepare_card.json | jq '.cards[].content.body[] | select(.type=="bullets") | .items'
```

#### 期待結果
- 階層構造が保持される（level値が0, 1など）
- 空行が適切な位置に`{"text": "", "level": 0}`として保持される

---

## UAT実行記録

### 実行環境
- **日時**: YYYY-MM-DD HH:MM
- **実行者**: @username
- **LLM Provider**: OpenAI / AWS Claude / Azure OpenAI
- **Model**: gpt-4 / claude-3-sonnet など
- **ブランチ**: feat/rm098-dynamic-blank-lines
- **コミット**: 644c3b0

### TC-1結果
- [ ] PASS
- [ ] FAIL

**詳細**:


### TC-2結果
- [ ] PASS
- [ ] FAIL

**詳細**:


### TC-3結果
- [ ] PASS
- [ ] FAIL

**詳細**:


### TC-4結果
- [ ] PASS
- [ ] FAIL

**詳細**:


---

## 問題発生時の対応

### buNoneエラーが発生した場合
1. `generate_ready.json`のbulletsブロックを確認
2. 空行が`{"text": "", "level": 0}`として含まれているか確認
3. ない場合、`prepare_card.json`を確認
4. LLMがプロンプトを正しく解釈していない可能性→プロンプト調整

### 空行が保持されない場合
1. `prepare_card.json`を確認
2. LLMの応答ログを確認（`--verbose`オプション使用）
3. プロンプトに空行指示が含まれているか再確認

---

## 完了条件
- [ ] TC-1〜TC-4すべてPASS
- [ ] 生成されたPPTXで空行が視覚的に確認できる
- [ ] `buNone`エラーが発生しない
- [ ] 既存機能（空行なし）も正常動作