from __future__ import annotations

import logging
from typing import Any, Tuple

from ...models import Slide, SlideBullet
from .issues import IssueTracker
from .options import AnalyzerOptions
from .snapshot import BulletParagraphResolver, ParagraphSnapshot, SlideSnapshot
from .utils import contrast_ratio, normalize_hex

logger = logging.getLogger(__name__)


def analyze_bullet_groups(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide_spec: Slide,
    snapshot: SlideSnapshot,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []

    resolver = BulletParagraphResolver(snapshot)
    applied_level: int | None = None
    previous_level: int | None = None

    for group in slide_spec.bullets:
        for bullet in group.items:
            bullet_issues, bullet_fixes, applied_level, previous_level = _evaluate_bullet(
                options,
                issue_tracker,
                slide_spec,
                bullet,
                group.anchor,
                resolver,
                applied_level,
                previous_level,
            )
            issues.extend(bullet_issues)
            fixes.extend(bullet_fixes)

    return issues, fixes


def _evaluate_bullet(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide_spec: Slide,
    bullet: SlideBullet,
    anchor: str | None,
    resolver: BulletParagraphResolver,
    applied_level: int | None,
    previous_level: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int | None, int | None]:
    issues: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []

    paragraph = resolver.resolve(anchor)
    actual_level = paragraph.level if paragraph else bullet.level
    target = {
        "slide_id": slide_spec.id,
        "element_id": bullet.id,
        "element_type": "bullet",
    }

    depth = _check_bullet_depth(options, issue_tracker, slide_spec, bullet, actual_level, target)
    issue_tracker.extend_results(issues, fixes, depth)

    font = _check_font_size(options, issue_tracker, slide_spec, bullet, paragraph, target)
    issue_tracker.extend_results(issues, fixes, font)

    contrast = _check_contrast(options, issue_tracker, slide_spec, bullet, paragraph, target)
    issue_tracker.extend_results(issues, fixes, contrast)

    updated_applied_level = _resolve_bullet_level(
        options,
        issue_tracker,
        slide_spec,
        bullet,
        actual_level,
        target,
        applied_level,
        previous_level,
        issues,
        fixes,
    )

    if paragraph is None:
        logger.debug(
            "箇条書き '%s' に対応する PPTX 段落が見つかりませんでした (slide=%s, anchor=%s)",
            bullet.id,
            slide_spec.id,
            anchor,
        )

    return issues, fixes, updated_applied_level, actual_level


def _resolve_bullet_level(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide_spec: Slide,
    bullet: SlideBullet,
    actual_level: int,
    target: dict[str, Any],
    applied_level: int | None,
    previous_level: int | None,
    issues: list[dict[str, Any]],
    fixes: list[dict[str, Any]],
) -> int | None:
    allowed_level = 0 if applied_level is None else min(applied_level + 1, options.max_bullet_level)
    if actual_level > allowed_level:
        issue_id = issue_tracker.next_issue_id("layout_consistency", slide_spec.id, bullet.id)
        fix = {
            "id": f"fix-{issue_id}",
            "issue_id": issue_id,
            "type": "bullet_reindent",
            "target": target,
            "payload": {"level": allowed_level},
        }
        issue = issue_tracker.make_issue(
            issue_id=issue_id,
            issue_type="layout_consistency",
            severity="warning",
            message=(
                f"スライド '{slide_spec.id}' の箇条書き '{bullet.id}' のレベル {actual_level} が"
                f" 許容ステップ {allowed_level} を超えています"
            ),
            target=target,
            metrics={
                "level": actual_level,
                "allowed_level": allowed_level,
                "previous_level": previous_level,
            },
            fix=fix,
        )
        issues.append(issue)
        if fix:
            fixes.append(fix)
        return allowed_level
    return actual_level


def _check_bullet_depth(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide: Slide,
    bullet: SlideBullet,
    actual_level: int,
    target: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if actual_level <= options.max_bullet_level:
        return None

    issue_id = issue_tracker.next_issue_id("bullet_depth", slide.id, bullet.id)
    fix = {
        "id": f"fix-{issue_id}",
        "issue_id": issue_id,
        "type": "bullet_cap",
        "target": target,
        "payload": {"level": options.max_bullet_level},
    }
    issue = issue_tracker.make_issue(
        issue_id=issue_id,
        issue_type="bullet_depth",
        severity="warning",
        message=(
            f"スライド '{slide.id}' の箇条書き '{bullet.id}' のレベルが"
            f" 上限 {options.max_bullet_level} を超えています"
        ),
        target=target,
        metrics={
            "level": actual_level,
            "max_level": options.max_bullet_level,
        },
        fix=fix,
    )
    return issue, fix


def _check_font_size(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide: Slide,
    bullet: SlideBullet,
    paragraph: ParagraphSnapshot | None,
    target: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    size = paragraph.font_size_pt if paragraph and paragraph.font_size_pt is not None else None
    if size is None:
        size = options.default_font_size

    if size >= options.min_font_size:
        return None

    issue_id = issue_tracker.next_issue_id("font_min", slide.id, bullet.id)
    fix = {
        "id": f"fix-{issue_id}",
        "issue_id": issue_id,
        "type": "font_raise",
        "target": target,
        "payload": {"size_pt": options.min_font_size},
    }
    issue = issue_tracker.make_issue(
        issue_id=issue_id,
        issue_type="font_min",
        severity="warning",
        message=(
            f"スライド '{slide.id}' の箇条書き '{bullet.id}' のフォントサイズ {size:.1f}pt が"
            f" 下限 {options.min_font_size:.1f}pt を下回っています"
        ),
        target=target,
        metrics={
            "size_pt": size,
            "min_size_pt": options.min_font_size,
            "shape_name": paragraph.shape_name if paragraph else None,
        },
        fix=fix,
    )
    return issue, fix


def _check_contrast(
    options: AnalyzerOptions,
    issue_tracker: IssueTracker,
    slide: Slide,
    bullet: SlideBullet,
    paragraph: ParagraphSnapshot | None,
    target: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    color_hex = (
        paragraph.color_hex if paragraph and paragraph.color_hex else options.default_font_color
    )
    font_size = (
        paragraph.font_size_pt if paragraph and paragraph.font_size_pt else options.default_font_size
    )
    try:
        ratio = contrast_ratio(color_hex, options.background_color)
    except ValueError:
        logger.debug("無効なカラーコードのためコントラスト判定をスキップ: %s", color_hex)
        return None

    required_ratio = options.min_contrast_ratio
    if font_size >= options.large_text_threshold_pt:
        required_ratio = min(required_ratio, options.large_text_min_contrast)

    if ratio >= required_ratio:
        return None

    issue_id = issue_tracker.next_issue_id("contrast_low", slide.id, bullet.id)
    suggested_color = options.preferred_text_color or options.default_font_color
    fix = {
        "id": f"fix-{issue_id}",
        "issue_id": issue_id,
        "type": "color_adjust",
        "target": target,
        "payload": {"color_hex": suggested_color},
    }
    issue = issue_tracker.make_issue(
        issue_id=issue_id,
        issue_type="contrast_low",
        severity="warning",
        message=(
            f"スライド '{slide.id}' の箇条書き '{bullet.id}' の文字色と背景色のコントラスト比"
            f" {ratio:.2f} が基準 {required_ratio:.2f} を下回っています"
        ),
        target=target,
        metrics={
            "color_hex": normalize_hex(color_hex),
            "background_hex": normalize_hex(options.background_color),
            "contrast_ratio": ratio,
            "required_ratio": required_ratio,
            "font_size_pt": font_size,
            "shape_name": paragraph.shape_name if paragraph else None,
        },
        fix=fix,
    )
    return issue, fix
