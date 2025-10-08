"""PPTX の自動診断ステップ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Slide, SlideBullet, SlideImage
from .base import PipelineContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalyzerOptions:
    output_filename: str = "analysis.json"
    min_font_size: float = 18.0
    min_contrast_ratio: float = 4.5
    large_text_min_contrast: float = 3.0
    large_text_threshold_pt: float = 18.0
    max_bullet_level: int = 3
    margin_in: float = 0.5
    slide_width_in: float = 10.0
    slide_height_in: float = 7.5
    default_font_size: float = 18.0
    default_font_color: str = "#333333"
    preferred_text_color: str | None = None
    background_color: str = "#FFFFFF"


class SimpleAnalyzerStep:
    """簡易的な品質診断を実行し、analysis.json を生成する。"""

    name = "analyzer"

    def __init__(self, options: AnalyzerOptions | None = None) -> None:
        self.options = options or AnalyzerOptions()
        self._sequence = 0

    def run(self, context: PipelineContext) -> None:
        issues: list[dict[str, Any]] = []
        fixes: list[dict[str, Any]] = []

        for slide in context.spec.slides:
            slide_issues, slide_fixes = self._analyze_slide(slide)
            issues.extend(slide_issues)
            fixes.extend(slide_fixes)

        analysis = {
            "slides": len(context.spec.slides),
            "meta": context.spec.meta.model_dump(),
            "issues": issues,
            "fixes": fixes,
        }
        output_path = self._save(analysis, context.workdir)
        context.add_artifact("analysis_path", output_path)
        logger.info("analysis.json を出力しました: %s", output_path)

    def _analyze_slide(self, slide: Slide) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        issues: list[dict[str, Any]] = []
        fixes: list[dict[str, Any]] = []

        for bullet in slide.bullets:
            bullet_issue = self._check_bullet_depth(slide, bullet)
            if bullet_issue:
                issue, fix = bullet_issue
                issues.append(issue)
                if fix:
                    fixes.append(fix)

            font_issue = self._check_font_size(slide, bullet)
            if font_issue:
                issue, fix = font_issue
                issues.append(issue)
                if fix:
                    fixes.append(fix)

            contrast_issue = self._check_contrast(slide, bullet)
            if contrast_issue:
                issue, fix = contrast_issue
                issues.append(issue)
                if fix:
                    fixes.append(fix)

        for image in slide.images:
            margin_issue = self._check_margins(slide, image)
            if margin_issue:
                issue, fix = margin_issue
                issues.append(issue)
                if fix:
                    fixes.append(fix)

        layout_issues, layout_fixes = self._check_layout_consistency(slide)
        issues.extend(layout_issues)
        fixes.extend(layout_fixes)

        return issues, fixes

    def _check_bullet_depth(
        self, slide: Slide, bullet: SlideBullet
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        if bullet.level <= self.options.max_bullet_level:
            return None

        target = {
            "slide_id": slide.id,
            "element_id": bullet.id,
            "element_type": "bullet",
        }
        issue_id = self._next_issue_id("bullet_depth", slide.id, bullet.id)
        message = (
            f"スライド '{slide.id}' の箇条書き '{bullet.id}' のレベルが"
            f" 上限 {self.options.max_bullet_level} を超えています"
        )
        fix = {
            "id": f"fix-{issue_id}",
            "issue_id": issue_id,
            "type": "bullet_cap",
            "target": target,
            "payload": {"level": self.options.max_bullet_level},
        }
        issue = self._make_issue(
            issue_id=issue_id,
            issue_type="bullet_depth",
            severity="warning",
            message=message,
            target=target,
            metrics={"level": bullet.level, "max_level": self.options.max_bullet_level},
            fix=fix,
        )
        return issue, fix

    def _check_font_size(
        self, slide: Slide, bullet: SlideBullet
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        font_spec = bullet.font
        size = font_spec.size_pt if font_spec and font_spec.size_pt else self.options.default_font_size
        if size >= self.options.min_font_size:
            return None

        target = {
            "slide_id": slide.id,
            "element_id": bullet.id,
            "element_type": "bullet",
        }
        issue_id = self._next_issue_id("font_min", slide.id, bullet.id)
        message = (
            f"スライド '{slide.id}' の箇条書き '{bullet.id}' のフォントサイズ {size:.1f}pt が"
            f" 下限 {self.options.min_font_size:.1f}pt を下回っています"
        )
        fix = {
            "id": f"fix-{issue_id}",
            "issue_id": issue_id,
            "type": "font_raise",
            "target": target,
            "payload": {"size_pt": self.options.min_font_size},
        }
        issue = self._make_issue(
            issue_id=issue_id,
            issue_type="font_min",
            severity="warning",
            message=message,
            target=target,
            metrics={"size_pt": size, "min_size_pt": self.options.min_font_size},
            fix=fix,
        )
        return issue, fix

    def _check_contrast(
        self, slide: Slide, bullet: SlideBullet
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        font_spec = bullet.font
        color_hex = font_spec.color_hex if font_spec and font_spec.color_hex else self.options.default_font_color
        font_size = (
            font_spec.size_pt if font_spec and font_spec.size_pt else self.options.default_font_size
        )
        try:
            ratio = _contrast_ratio(color_hex, self.options.background_color)
        except ValueError:
            logger.debug("無効なカラーコードのためコントラスト判定をスキップ: %s", color_hex)
            return None

        required_ratio = self.options.min_contrast_ratio
        if font_size >= self.options.large_text_threshold_pt:
            required_ratio = min(required_ratio, self.options.large_text_min_contrast)

        if ratio >= required_ratio:
            return None

        target = {
            "slide_id": slide.id,
            "element_id": bullet.id,
            "element_type": "bullet",
        }
        issue_id = self._next_issue_id("contrast_low", slide.id, bullet.id)
        message = (
            f"スライド '{slide.id}' の箇条書き '{bullet.id}' の文字色と背景色のコントラスト比"
            f" {ratio:.2f} が基準 {required_ratio:.2f} を下回っています"
        )
        suggested_color = self.options.preferred_text_color or self.options.default_font_color
        fix = {
            "id": f"fix-{issue_id}",
            "issue_id": issue_id,
            "type": "color_adjust",
            "target": target,
            "payload": {"color_hex": suggested_color},
        }
        issue = self._make_issue(
            issue_id=issue_id,
            issue_type="contrast_low",
            severity="warning",
            message=message,
            target=target,
            metrics={
                "color_hex": _normalize_hex(color_hex),
                "background_hex": _normalize_hex(self.options.background_color),
                "contrast_ratio": ratio,
                "required_ratio": required_ratio,
                "font_size_pt": font_size,
            },
            fix=fix,
        )
        return issue, fix

    def _check_layout_consistency(
        self, slide: Slide
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        issues: list[dict[str, Any]] = []
        fixes: list[dict[str, Any]] = []
        previous_level: int | None = None
        applied_level: int | None = None

        for bullet in slide.bullets:
            allowed_level = 0 if applied_level is None else min(applied_level + 1, self.options.max_bullet_level)
            if bullet.level <= allowed_level:
                applied_level = bullet.level
                previous_level = bullet.level
                continue

            target_level = allowed_level
            target = {
                "slide_id": slide.id,
                "element_id": bullet.id,
                "element_type": "bullet",
            }
            issue_id = self._next_issue_id("layout_consistency", slide.id, bullet.id)
            message = (
                f"スライド '{slide.id}' の箇条書き '{bullet.id}' のレベル {bullet.level} が"
                f" 許容ステップ {allowed_level} を超えています"
            )
            fix = {
                "id": f"fix-{issue_id}",
                "issue_id": issue_id,
                "type": "bullet_reindent",
                "target": target,
                "payload": {"level": target_level},
            }
            issue = self._make_issue(
                issue_id=issue_id,
                issue_type="layout_consistency",
                severity="warning",
                message=message,
                target=target,
                metrics={
                    "level": bullet.level,
                    "allowed_level": allowed_level,
                    "previous_level": previous_level,
                },
                fix=fix,
            )
            issues.append(issue)
            fixes.append(fix)
            applied_level = target_level
            previous_level = bullet.level

        return issues, fixes

    def _check_margins(
        self, slide: Slide, image: SlideImage
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        left = image.left_in
        top = image.top_in
        width = image.width_in
        height = image.height_in
        margin = self.options.margin_in

        violations: list[str] = []
        if left is not None and left < margin:
            violations.append("left")
        if top is not None and top < margin:
            violations.append("top")
        if left is not None and width is not None:
            right = left + width
            if right > self.options.slide_width_in - margin:
                violations.append("right")
        if top is not None and height is not None:
            bottom = top + height
            if bottom > self.options.slide_height_in - margin:
                violations.append("bottom")

        if not violations:
            return None

        target = {
            "slide_id": slide.id,
            "element_id": image.id,
            "element_type": "image",
        }
        issue_id = self._next_issue_id("margin", slide.id, image.id)
        message = (
            f"スライド '{slide.id}' の画像 '{image.id}' が余白基準 {margin:.1f}in を外れています"
        )

        target_left = left
        if left is not None:
            usable_width = self.options.slide_width_in - 2 * margin
            shape_width = width or 0.0
            max_left = self.options.slide_width_in - margin - shape_width
            max_left = max(max_left, margin)
            min_left = margin
            target_left = min(max(left, min_left), max_left if usable_width >= 0 else margin)

        target_top = top
        if top is not None:
            usable_height = self.options.slide_height_in - 2 * margin
            shape_height = height or 0.0
            max_top = self.options.slide_height_in - margin - shape_height
            max_top = max(max_top, margin)
            min_top = margin
            target_top = min(max(top, min_top), max_top if usable_height >= 0 else margin)

        fix_payload: dict[str, float] = {}
        if target_left is not None and left is not None and abs(target_left - left) > 1e-3:
            fix_payload["left_in"] = round(target_left, 3)
        if target_top is not None and top is not None and abs(target_top - top) > 1e-3:
            fix_payload["top_in"] = round(target_top, 3)

        fix = None
        if fix_payload:
            fix = {
                "id": f"fix-{issue_id}",
                "issue_id": issue_id,
                "type": "move",
                "target": target,
                "payload": fix_payload,
            }

        issue = self._make_issue(
            issue_id=issue_id,
            issue_type="margin",
            severity="warning",
            message=message,
            target=target,
            metrics={
                "left_in": left,
                "top_in": top,
                "width_in": width,
                "height_in": height,
                "margin_in": margin,
                "violations": violations,
            },
            fix=fix,
        )
        return issue, fix

    def _next_issue_id(self, issue_type: str, slide_id: str, element_id: str | None) -> str:
        self._sequence += 1
        parts = [issue_type, slide_id]
        if element_id:
            parts.append(element_id)
        parts.append(str(self._sequence))
        return "-".join(parts)

    def _make_issue(
        self,
        *,
        issue_id: str,
        issue_type: str,
        severity: str,
        message: str,
        target: dict[str, Any],
        metrics: dict[str, Any],
        fix: dict[str, Any] | None,
    ) -> dict[str, Any]:
        issue = {
            "id": issue_id,
            "type": issue_type,
            "severity": severity,
            "message": message,
            "target": target,
            "metrics": metrics,
        }
        if fix:
            issue["fix"] = fix
        return issue

    def _save(self, payload: dict[str, Any], workdir: Path) -> Path:
        output_dir = workdir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self.options.output_filename
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path


def _normalize_hex(value: str) -> str:
    return value if value.startswith("#") else f"#{value}"


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    hex_value = _normalize_hex(value).lstrip("#")
    if len(hex_value) != 6:
        raise ValueError("hex color must be 6 characters")
    r = int(hex_value[0:2], 16)
    g = int(hex_value[2:4], 16)
    b = int(hex_value[4:6], 16)
    return r / 255.0, g / 255.0, b / 255.0


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def linearize(channel: float) -> float:
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = (linearize(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(foreground_hex: str, background_hex: str) -> float:
    fg_lum = _relative_luminance(_hex_to_rgb(foreground_hex))
    bg_lum = _relative_luminance(_hex_to_rgb(background_hex))
    lighter = max(fg_lum, bg_lum)
    darker = min(fg_lum, bg_lum)
    return (lighter + 0.05) / (darker + 0.05)
