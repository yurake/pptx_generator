"""analysis.json の Fix を簡易適用するステップ。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..models import FontSpec, Slide, SlideBullet
from .base import PipelineContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RefinerOptions:
    """Refiner の動作設定。"""

    max_bullet_level: int = 3
    enable_bullet_reindent: bool = True
    enable_font_raise: bool = False
    min_font_size: float = 18.0
    enable_color_adjust: bool = False
    preferred_text_color: str | None = None
    fallback_font_color: str = "#333333"
    default_font_name: str | None = None


class SimpleRefinerStep:
    """ジョブ仕様の簡易自動補正を行うステップ。"""

    name = "refiner"

    def __init__(self, options: RefinerOptions | None = None) -> None:
        self.options = options or RefinerOptions()

    def run(self, context: PipelineContext) -> None:
        adjustments: list[dict[str, Any]] = []

        for slide in context.spec.slides:
            if self.options.enable_bullet_reindent:
                adjustments.extend(self._apply_bullet_reindent(slide))
            else:
                logger.debug("bullet_reindent を無効化しています: slide=%s", slide.id)

            if self.options.enable_font_raise or self.options.enable_color_adjust:
                adjustments.extend(self._apply_typography_adjustments(slide))
            else:
                logger.debug("フォント・カラー自動調整を無効化しています: slide=%s", slide.id)

        context.add_artifact("refiner_adjustments", adjustments)
        logger.info("Refiner を実行しました: %d 件調整", len(adjustments))

    def _apply_bullet_reindent(self, slide: Slide) -> list[dict[str, Any]]:
        adjustments: list[dict[str, Any]] = []
        applied_level: int | None = None

        for bullet in slide.iter_bullets():
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

    def _apply_typography_adjustments(self, slide: Slide) -> list[dict[str, Any]]:
        adjustments: list[dict[str, Any]] = []
        for bullet in slide.iter_bullets():
            font = bullet.font
            created_font = False
            if font is None:
                if not self.options.default_font_name:
                    logger.debug(
                        "font_spec が未設定のため調整をスキップ: slide=%s bullet=%s",
                        slide.id,
                        bullet.id,
                    )
                    continue
                font = FontSpec(
                    name=self.options.default_font_name,
                    size_pt=self.options.min_font_size,
                    color_hex=_normalize_hex(
                        self.options.preferred_text_color
                        or self.options.fallback_font_color
                    ),
                )
                bullet.font = font
                created_font = True

            if self.options.enable_font_raise:
                target_size = max(font.size_pt, self.options.min_font_size)
                if target_size > font.size_pt + 1e-3:
                    original_size = font.size_pt
                    font.size_pt = target_size
                    adjustments.append(
                        {
                            "slide_id": slide.id,
                            "element_id": bullet.id,
                            "type": "font_raise",
                            "from_size_pt": original_size,
                            "to_size_pt": target_size,
                        }
                    )

            if self.options.enable_color_adjust:
                target_color = _normalize_hex(
                    self.options.preferred_text_color
                    or self.options.fallback_font_color
                )
                current_color = _normalize_hex(font.color_hex)
                if current_color.lower() != target_color.lower() or created_font:
                    font.color_hex = target_color
                    adjustments.append(
                        {
                            "slide_id": slide.id,
                            "element_id": bullet.id,
                            "type": "color_adjust",
                            "from_color_hex": current_color if not created_font else None,
                            "to_color_hex": target_color,
                        }
                    )

        return adjustments


def _normalize_hex(value: str) -> str:
    return value if value.startswith("#") else f"#{value}"
