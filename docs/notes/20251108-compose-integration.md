---
title: stage 4・5統合 `pptx compose` 取り込みメモ
created: 2025-11-08
tags:
  - cli
  - pipeline
  - roadmap:RM-049
---

## 背景
- main ブランチに stage 4・5統合機能 (`pptx compose`) が追加され、`generate_ready.json` を前提とした CLI ハンドリングに切り替わった。
- feat/rm049-pptx-gen-scope ブランチでは stage 5 専用 `pptx gen` を実装していたため、仕様差分の吸収と責務再整理が必要だった。

## 対応概要
- `pptx gen` は stage 6 専用コマンドのまま維持し、`generate_ready.json` 入力＋テンプレ自動解決フローを確定。
- `pptx render` 互換ラッパーを廃止し、stage 5 は `pptx mapping` / `pptx compose` で `generate_ready.json` を生成してから `pptx gen` へ渡す運用に整理。
- パイプラインのアーティファクトキーと成果物の命名を `generate_ready` 系へ統一し、監査ログやマッピングメタの整合を確認。
- CLI 統合テストを compose / mapping / gen の 3 経路で更新し、生成物ハッシュやログパスの検証を `generate_ready` 前提で再実装。
- README や CLI コマンドガイドを更新し、`render` と `gen` の役割分担、compose を軸とした stage 4/5フローを明記。

## 残課題・フォローアップ
- 旧 `docs/design/archive/stage3-4-cli.md` は削除済み。compose ベースの図表を `docs/design/stages/stage-03-compose.md` へ統合する。
- `.egg-info` 配下の生成メタには旧 `rendering_ready` 文言が残っているため、次回の配布物生成時に `generate_ready` へ更新されることを確認する。
