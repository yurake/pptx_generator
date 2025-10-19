---
title: Polisher 適用範囲の再整理
date: 2025-10-19
author: Automation Team
related:
  - docs/roadmap/roadmap.md#rm-014
  - docs/roadmap/roadmap.md#rm-033
---

## 背景
- RM-014 の実装過程で Open XML Polisher を工程6へ組み込んだ。
- Polisher が担うべき範囲と、Renderer／Refiner で完結させたい処理の切り分けが曖昧。
- 将来的に「仕上げ工程は最小限のフォールバックのみ」という方針を徹底するため、役割を再確認した。

## 確認結果
- Polisher で実装済みの `font size raise` / `font color unify` は Refiner でも実現可能で、重複が発生している。  
  → 今後は Renderer／Refiner 側で確実に適用できるように整理する。
- ただし Refiner が対象にしているのは箇条書き (`SlideBullet`) に限定されており、テキストボックス・ノート・表セルなど他の `Run` には波及していない。  
  → Polisher で全 Run を走査する意義は残るが、Renderer／Refiner が段階で漏れなく適用できるエリアを広げることが優先。
- ParagraphProperties の生成までは Polisher で対応したが、段落間隔・余白・揃えなどの値は設定していない。  
  → Renderer がブランド設定に基づき段落スタイルを完全適用する仕組みを先に整える。
- Polisher でのみ必要な処理は「テンプレート側の漏れ補正」「Open XML に直接触らないと修正できないケース」「監査ログへの補正件数記録」に限定する想定。

## 次のアクション
1. Renderer 改修  
   - ブランド設定 (`branding.json`) から段落揃え、行間、段落前後余白、インデントなどを取得し、描画段階で適用する。  
   - Refiner と重複するフォント・カラー補正の整理も合わせて検討する。
2. テスト整備  
   - 上記の段落書式がレンダリング結果へ反映されることを CLI / 単体テストで検証する。
3. Polisher の役割再定義  
   - Renderer 側で適用できる処理を移行した後、Polisher は “最終チェックとフォールバック” に scope down する。  
   - 監査ログや CLI 出力で Polisher が何を補正したか分かるように維持する。

これらを RM-034 としてロードマップに追加し、実装タスクを別途管理する。
