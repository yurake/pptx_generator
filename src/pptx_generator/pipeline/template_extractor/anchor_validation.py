"""Mixins for anchor validation logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from .errors import DuplicateAnchorError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..models import ShapeInfo

__all__ = ["AnchorValidationMixin"]


class AnchorValidationMixin:
    """Provides anchor validation helpers."""

    def _check_duplicate_anchors(
        self,
        anchors: list["ShapeInfo"],
        layout_name: str | None,
        index: int,
        source_mode: Literal["slide", "template"],
    ) -> None:
        anchor_names: dict[str, list[int]] = {}

        for idx, shape_info in enumerate(anchors):
            name = shape_info.name
            if not name or name.startswith("unnamed_"):
                continue

            if name not in anchor_names:
                anchor_names[name] = []
            anchor_names[name].append(idx)

        duplicates = {
            name: indices for name, indices in anchor_names.items() if len(indices) > 1
        }

        if not duplicates:
            return

        source_label = "スライド" if source_mode == "slide" else "レイアウト"
        layout_display = layout_name or f"{source_label}-{index:02d}"
        source_desc = (
            "実スライド (layout_mode=static/from=slide)"
            if source_mode == "slide"
            else "スライドマスター (layout_mode=dynamic または static/from=template)"
        )

        error_lines = [
            f"同一{source_label}内でアンカー名が重複しています:",
            f"  - 抽出ソース: {source_desc}",
            f"  - {source_label}: {layout_display} (index={index})",
        ]

        for dup_name, indices in duplicates.items():
            error_lines.append(
                f"  - 重複アンカー: '{dup_name}' (出現回数: {len(indices)})"
            )

        error_lines.extend(
            [
                "",
                "修正方法:",
                "  PowerPoint で該当図形を選択し、図形名を一意にリネームしてください。",
                "  図形名は「ホーム」→「選択」→「オブジェクトの選択と表示」で確認・変更できます。",
            ]
        )

        raise DuplicateAnchorError("\n".join(error_lines))
