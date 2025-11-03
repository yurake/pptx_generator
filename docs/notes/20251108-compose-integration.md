---
title: 工程4・5統合 `pptx compose` 取り込みメモ
created: 2025-11-08
tags:
  - cli
  - pipeline
  - roadmap:RM-049
---

## 背景
- main ブランチに工程4・5統合機能 (`pptx compose`) が追加され、`rendering_ready.json` や CLI ハンドリングが大きく変更された。
- feat/rm049-pptx-gen-scope ブランチでは工程5専用 `pptx gen` を実装していたため、仕様差分の吸収と責務再整理が必要だった。

## 対応概要
- `pptx gen` を JobSpec 入力前提のファサードへ戻し、工程4 (mapping) → 工程5 (render) を内部で連結。
- `pptx render` 互換ラッパーを廃止し、工程5は `pptx gen` からの一括実行に集約。
- パイプラインのアーティファクトキーと成果物の命名を `generate_ready` 系へ統一し、監査ログやマッピングメタの整合を確認。
- CLI 統合テストを compose / render / gen の 3 経路で更新し、生成物ハッシュやログパスの検証を `generate_ready` 前提で再実装。
- README や CLI コマンドガイドを更新し、`render` と `gen` の役割分担、compose を軸とした工程4/5フローを明記。

## 残課題・フォローアップ
- `docs/design/20251019-stage3-4-cli.md` などの検討メモは次回整理時に compose ベースの図表へ差し替える。
- `.egg-info` 配下の生成メタには `rendering_ready` 文言が残っているため、次回の配布物生成時に自動更新されることを確認する。
