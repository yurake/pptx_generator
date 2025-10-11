## pptx-pythonテンプレート検証結果（2025-10-05）

- .potx（PowerPointテンプレート）ファイルは、pptx-pythonライブラリで直接テンプレートとして利用できない。
- 拡張子を .pptx に変更しても、content-typeがテンプレートのままなのでエラーとなる。
- pptx-pythonでテンプレート利用する場合は、.pptx形式のファイルを用意する必要がある。
- .potxから新規 .pptx を生成するには、PowerPointアプリ等で「テンプレートから新規作成」操作が必要。

## skeleton.pptx テンプレート検証結果（2025-10-05）

- samples/skeleton.pptx をテンプレートとして指定し、CLI（uv run pptx gen samples/json/sample_spec.json --template samples/skeleton.pptx）で PPTX生成が正常に完了した。
- 出力ファイル: .pptxgen/outputs/proposal.pptx
- 仕様通りにレイアウト・フォント・画像が反映されていることを確認。
- .potx形式は直接利用できないが、.pptx形式のテンプレートであれば問題なく動作する。

### 注意: テンプレートファイルは .pptx のみ対応（.potxは未対応）

- CLIの --template オプションには .pptx 形式のみ指定可能です。
- .potx テンプレートを利用したい場合は、PowerPointで新規 .pptx として保存してください。
