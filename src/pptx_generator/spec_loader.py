"""JobSpec と JobSpecScaffold の読み込み・変換ユーティリティ。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import logging
from pathlib import Path

from pydantic import ValidationError

from .models import (
    JobAuth,
    JobMeta,
    JobSpec,
    JobSpecScaffold,
    JobSpecScaffoldPlaceholder,
    JobSpecScaffoldSlide,
    Slide,
    SlideTextbox,
    SpecValidationError,
    TextboxPosition,
)

logger = logging.getLogger(__name__)


def load_jobspec_from_path(path: Path) -> JobSpec:
    """JobSpec または JobSpecScaffold を読み込んで JobSpec を返す。"""

    text = Path(path).read_text(encoding="utf-8")
    try:
        return JobSpec.model_validate_json(text)
    except ValidationError as exc:
        jobspec_error = SpecValidationError.from_validation_error(exc)

    try:
        scaffold = JobSpecScaffold.model_validate_json(text)
    except ValidationError:
        raise jobspec_error

    logger.info("JobSpecScaffold を JobSpec へ変換します: path=%s", path)
    return convert_scaffold_to_jobspec(scaffold)


def convert_scaffold_to_jobspec(scaffold: JobSpecScaffold) -> JobSpec:
    """JobSpecScaffold から JobSpec を生成する。"""

    meta = _convert_meta(scaffold)
    auth = _convert_auth(scaffold)
    slides = [_convert_slide(slide) for slide in scaffold.slides]
    return JobSpec(meta=meta, auth=auth, slides=slides)


def _convert_meta(scaffold: JobSpecScaffold) -> JobMeta:
    template_path = Path(scaffold.meta.template_path)
    title_source = scaffold.meta.template_id or template_path.stem
    title = title_source or "Template Draft"
    created_at = _normalize_timestamp(scaffold.meta.generated_at)
    return JobMeta(
        schema_version=scaffold.meta.schema_version,
        title=title,
        created_at=created_at,
        locale="ja-JP",
        template_path=str(template_path),
        template_id=scaffold.meta.template_id,
        layout_count=scaffold.meta.layout_count,
        layouts_path=scaffold.meta.layouts_path,
        template_spec_path=scaffold.meta.template_spec_path,
    )


def _convert_auth(scaffold: JobSpecScaffold) -> JobAuth:
    template_path = Path(scaffold.meta.template_path)
    creator = scaffold.meta.template_id or template_path.stem or "template_extractor"
    return JobAuth(created_by=creator)


def _convert_slide(scaffold_slide: JobSpecScaffoldSlide) -> Slide:
    title: str | None = None
    subtitle: str | None = None
    textboxes: list[SlideTextbox] = []
    notes_entries: list[str] = []
    auto_draw_anchors: list[str] = []
    auto_draw_boxes: dict[str, TextboxPosition] = {}

    counters = defaultdict(int)

    for placeholder in scaffold_slide.placeholders:
        if placeholder.auto_draw:
            if placeholder.anchor:
                auto_draw_anchors.append(placeholder.anchor)
                auto_draw_boxes[placeholder.anchor] = TextboxPosition(
                    left_in=placeholder.bounds.left_in,
                    top_in=placeholder.bounds.top_in,
                    width_in=placeholder.bounds.width_in,
                    height_in=placeholder.bounds.height_in,
                )
            continue
        placeholder_type = (placeholder.placeholder_type or "").upper()
        if placeholder.kind == "text":
            title, subtitle, textboxes = _apply_text_placeholder(
                scaffold_slide,
                placeholder,
                placeholder_type,
                title,
                subtitle,
                textboxes,
                counters,
            )
        else:
            notes_entries.append(_format_placeholder_note(placeholder))

    notes = "\n".join(notes_entries) if notes_entries else None
    return Slide(
        id=scaffold_slide.id,
        layout=scaffold_slide.layout,
        title=title,
        subtitle=subtitle,
        notes=notes,
        textboxes=textboxes,
        auto_draw_anchors=auto_draw_anchors,
        auto_draw_boxes=auto_draw_boxes,
    )


def _apply_text_placeholder(
    scaffold_slide: JobSpecScaffoldSlide,
    placeholder: JobSpecScaffoldPlaceholder,
    placeholder_type: str,
    title: str | None,
    subtitle: str | None,
    textboxes: list[SlideTextbox],
    counters: dict[str, int],
) -> tuple[str | None, str | None, list[SlideTextbox]]:
    sample_text = placeholder.sample_text or ""

    if placeholder_type in {"TITLE", "CENTER_TITLE"} and not title:
        title = sample_text
        return title, subtitle, textboxes

    if placeholder_type == "SUBTITLE" and not subtitle:
        subtitle = sample_text
        return title, subtitle, textboxes

    textbox_id = _next_identifier(scaffold_slide.id, "textbox", counters)
    position = TextboxPosition(
        left_in=placeholder.bounds.left_in,
        top_in=placeholder.bounds.top_in,
        width_in=placeholder.bounds.width_in,
        height_in=placeholder.bounds.height_in,
    )
    textboxes.append(
        SlideTextbox(
            id=textbox_id,
            text=sample_text,
            anchor=placeholder.anchor or None,
            position=position,
        )
    )
    return title, subtitle, textboxes


def _format_placeholder_note(placeholder: JobSpecScaffoldPlaceholder) -> str:
    anchor = placeholder.anchor or "(unnamed)"
    kind = placeholder.kind
    placeholder_type = placeholder.placeholder_type or ""
    sample = placeholder.sample_text or ""
    if placeholder.auto_draw:
        return f"[{anchor}] kind={kind} type={placeholder_type} auto_draw=true"
    return f"[{anchor}] kind={kind} type={placeholder_type} sample={sample}"


def _next_identifier(slide_id: str, prefix: str, counters: dict[str, int]) -> str:
    counters[prefix] += 1
    return f"{slide_id}-{prefix}-{counters[prefix]:02d}"


def _normalize_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        logger.debug("timestamp のパースに失敗したため現在時刻を利用: value=%s", value)
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()
