"""analysis.json の Fix を簡易適用するステップ。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..models import Slide, SlideBullet
from .base import PipelineContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RefinerOptions:
    """Refiner の動作設定。"""

    max_bullet_level: int = 3
    enable_bullet_reindent: bool = True


class SimpleRefinerStep:
    """ジョブ仕様の簡易自動補正を行うステップ。"""

    name = "refiner"

    def __init__(self, options: RefinerOptions | None = None) -> None:
        self.options = options or RefinerOptions()

    def run(self, context: PipelineContext) -> None:
        adjustments: list[dict[str, Any]] = []

        if not self.options.enable_bullet_reindent:
            logger.debug("bullet_reindent を無効化しているため Refiner をスキップ")
        else:
            for slide in context.spec.slides:
                slide_adjustments = self._apply_bullet_reindent(slide)
                adjustments.extend(slide_adjustments)

        context.add_artifact("refiner_adjustments", adjustments)
        logger.info("Refiner を実行しました: %d 件調整", len(adjustments))

    def _apply_bullet_reindent(self, slide: Slide) -> list[dict[str, Any]]:
        adjustments: list[dict[str, Any]] = []
        applied_level: int | None = None

        for bullet in slide.bullets:
            allowed_level = (
                0
                if applied_level is None
                else min(applied_level + 1, self.options.max_bullet_level)
            )
            original_level = bullet.level

            if original_level <= allowed_level:
                applied_level = original_level
                continue

            target_level = allowed_level
            self._update_bullet_level(bullet, target_level)
            applied_level = target_level
            adjustments.append(
                {
                    "slide_id": slide.id,
                    "element_id": bullet.id,
                    "type": "bullet_reindent",
                    "from_level": original_level,
                    "to_level": target_level,
                }
            )
            logger.debug(
                "bullet_reindent 適用: slide=%s bullet=%s %d -> %d",
                slide.id,
                bullet.id,
                original_level,
                target_level,
            )

        return adjustments

    @staticmethod
    def _update_bullet_level(bullet: SlideBullet, level: int) -> None:
        bullet.level = level
