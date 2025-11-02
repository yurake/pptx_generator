"""Generate Ready ドキュメントの補助ユーティリティ。"""

from __future__ import annotations

from itertools import count
from typing import Any

from .models import (ChartOptions, ChartSeries, JobAuth, JobMeta, JobSpec,
                     GenerateReadyDocument, GenerateReadySlide, Slide,
                     SlideBullet, SlideBulletGroup, SlideChart, SlideImage,
                     SlideTable, SlideTextbox)


def generate_ready_to_jobspec(document: GenerateReadyDocument) -> JobSpec:
    """generate_ready.json からレンダリング用の JobSpec を組み立てる。"""

    meta = document.meta.job_meta or JobMeta(
        schema_version="unknown",
        title="Untitled Deck",
        client=None,
        author=None,
        created_at=document.meta.generated_at,
        theme="default",
        locale="ja-JP",
    )
    auth = document.meta.job_auth or JobAuth(created_by="unknown")
    slides = [_build_slide(index, slide) for index, slide in enumerate(document.slides, start=1)]
    return JobSpec(meta=meta, auth=auth, slides=slides)


def _build_slide(index: int, slide: GenerateReadySlide) -> Slide:
    slide_id = _resolve_slide_id(index, slide)
    elements = slide.elements or {}
    title = _value_as_str(elements.get("title"))
    subtitle = _value_as_str(elements.get("subtitle"))
    notes = _value_as_str(elements.get("note"))

    bullet_groups: list[SlideBulletGroup] = []
    bullet_counter = count(1)

    body_value = elements.get("body")
    if isinstance(body_value, list):
        bullets = [_create_bullet(slide_id, None, next(bullet_counter), text) for text in body_value]
        if bullets:
            bullet_groups.append(SlideBulletGroup(anchor=None, items=bullets))

    tables: list[SlideTable] = []
    images: list[SlideImage] = []
    charts: list[SlideChart] = []
    textboxes: list[SlideTextbox] = []

    for key, value in elements.items():
        if key in {"title", "subtitle", "note", "body"}:
            continue
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            bullets = [
                _create_bullet(slide_id, key, next(bullet_counter), text) for text in value
            ]
            if bullets:
                bullet_groups.append(SlideBulletGroup(anchor=key, items=bullets))
            continue
        if isinstance(value, dict):
            if _looks_like_table(value):
                tables.append(
                    SlideTable(
                        id=key,
                        anchor=key,
                        columns=list(_iterate_str_list(value.get("headers", []))),
                        rows=[list(row) for row in _normalize_rows(value.get("rows", []))],
                        style=None,
                    )
                )
                continue
            if _looks_like_image(value):
                images.append(
                    SlideImage(
                        id=key,
                        anchor=key,
                        source=str(value["source"]),
                        sizing=value.get("sizing", "fit"),
                        left_in=value.get("left_in"),
                        top_in=value.get("top_in"),
                        width_in=value.get("width_in"),
                        height_in=value.get("height_in"),
                    )
                )
                continue
            if _looks_like_chart(value):
                charts.append(
                    SlideChart(
                        id=key,
                        anchor=key,
                        type=str(value["type"]),
                        categories=list(_iterate_str_list(value.get("categories", []))),
                        series=_build_chart_series(value.get("series", [])),
                        options=_build_chart_options(value.get("options")),
                    )
                )
                continue
            if _looks_like_textbox(value):
                textboxes.append(
                    SlideTextbox(
                        id=key,
                        anchor=key,
                        text=_value_as_str(value.get("text")) or "",
                    )
                )
                continue

    return Slide(
        id=slide_id,
        layout=slide.layout_id,
        title=title,
        subtitle=subtitle,
        notes=notes,
        bullets=bullet_groups,
        images=images,
        tables=tables,
        charts=charts,
        textboxes=textboxes,
    )


def _resolve_slide_id(index: int, slide: GenerateReadySlide) -> str:
    sources = slide.meta.sources
    if sources:
        candidate = sources[0]
        if isinstance(candidate, str) and candidate:
            return candidate
    return f"slide-{index}"


def _create_bullet(slide_id: str, anchor: str | None, sequence: int, text: str) -> SlideBullet:
    anchor_part = anchor or "body"
    bullet_id = f"{slide_id}-{anchor_part}-bullet-{sequence}"
    return SlideBullet(id=bullet_id, text=text, level=0)


def _value_as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _looks_like_table(value: dict[str, Any]) -> bool:
    return "rows" in value and isinstance(value.get("rows"), list)


def _normalize_rows(rows: list[Any]) -> list[list[str]]:
    normalized: list[list[str]] = []
    for row in rows:
        if isinstance(row, list):
            normalized.append([str(cell) for cell in row])
    return normalized


def _iterate_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item) for item in values]


def _looks_like_image(value: dict[str, Any]) -> bool:
    return "source" in value


def _looks_like_chart(value: dict[str, Any]) -> bool:
    return "type" in value and "series" in value


def _build_chart_series(series_payload: Any) -> list[ChartSeries]:
    series_list: list[ChartSeries] = []
    if not isinstance(series_payload, list):
        return series_list
    for index, item in enumerate(series_payload, start=1):
        if not isinstance(item, dict):
            continue
        series_list.append(
            ChartSeries(
                name=str(item.get("name", f"series-{index}")),
                values=[_coerce_number(value) for value in item.get("values", [])],
                color_hex=item.get("color_hex"),
            )
        )
    return series_list


def _build_chart_options(payload: Any) -> ChartOptions | None:
    if not isinstance(payload, dict):
        return None
    return ChartOptions(
        data_labels=bool(payload.get("data_labels", False)),
        y_axis_format=payload.get("y_axis_format"),
    )


def _looks_like_textbox(value: dict[str, Any]) -> bool:
    return "text" in value


def _coerce_number(value: Any) -> float | int:
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0
