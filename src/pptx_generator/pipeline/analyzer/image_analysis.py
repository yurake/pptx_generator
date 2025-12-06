from __future__ import annotations

import logging
from typing import Any

from ...models import Slide
from .issues import IssueTracker
from .layout_checks import check_grid_alignment, check_margins, locate_image_shape
from .options import AnalyzerOptions
from .snapshot import SlideSnapshot

logger = logging.getLogger(__name__)


def analyze_images(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide_spec: Slide,
    snapshot: SlideSnapshot,
    *,
    slide_width_in: float,
    slide_height_in: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []

    for image_spec in slide_spec.images:
        shape = locate_image_shape(snapshot, image_spec)
        if shape is None:
            logger.debug("画像 '%s' の図形が見つかりません", image_spec.id)
            continue
        result = check_margins(
            options,
            issue_tracker,
            slide_spec,
            image_spec,
            shape,
            slide_width_in=slide_width_in,
            slide_height_in=slide_height_in,
        )
        issue_tracker.extend_results(issues, fixes, result)

        grid = check_grid_alignment(
            options,
            issue_tracker,
            slide_spec,
            image_spec.id,
            "image",
            shape,
        )
        issue_tracker.extend_results(issues, fixes, grid)

    return issues, fixes
