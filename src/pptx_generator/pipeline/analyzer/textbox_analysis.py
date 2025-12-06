from __future__ import annotations

import logging
from typing import Any

from ...models import Slide
from .issues import IssueTracker
from .layout_checks import check_grid_alignment, locate_textbox_shape
from .options import AnalyzerOptions
from .snapshot import SlideSnapshot

logger = logging.getLogger(__name__)


def analyze_textboxes(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide_spec: Slide,
    snapshot: SlideSnapshot,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []

    for textbox in slide_spec.textboxes:
        shape = locate_textbox_shape(snapshot, textbox)
        if shape is None:
            logger.debug("テキストボックス '%s' の図形が見つかりません", textbox.id)
            continue
        grid = check_grid_alignment(
            options,
            issue_tracker,
            slide_spec,
            textbox.id,
            "textbox",
            shape,
        )
        issue_tracker.extend_results(issues, fixes, grid)

    return issues, fixes
