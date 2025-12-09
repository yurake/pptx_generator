"""Constants used by the template extractor."""

from __future__ import annotations

__all__ = [
    "SLIDE_BULLET_ANCHORS",
    "JOBSPEC_SCHEMA_VERSION",
    "MAX_SAMPLE_TEXT_LENGTH",
    "EMU_PER_INCH",
    "AUTO_DRAW_PLACEHOLDER_TYPES",
]

# SlideBullet拡張仕様で使用される可能性のあるアンカー名パターン
SLIDE_BULLET_ANCHORS = {"bullets", "bullet_list", "content", "body"}
JOBSPEC_SCHEMA_VERSION = "0.1"
MAX_SAMPLE_TEXT_LENGTH = 200
EMU_PER_INCH = 914400

# PowerPoint 側で自動描画されるプレースホルダー種別
AUTO_DRAW_PLACEHOLDER_TYPES = {
    "SLIDE_NUMBER",
    "DATE",
    "DATETIME",
    "FOOTER",
    "HEADER",
}
