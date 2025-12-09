"""Template extractor specific exceptions."""

from __future__ import annotations

__all__ = ["DuplicateAnchorError"]


class DuplicateAnchorError(RuntimeError):
    """アンカー名重複を通知する例外。"""
