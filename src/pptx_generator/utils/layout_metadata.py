"""Utilities for layout placeholder summarisation and heuristic usage tag derivation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence
from collections import Counter, defaultdict

PositionLabel = tuple[str, str]


@dataclass(slots=True)
class HeuristicUsageTagsResult:
    tags: set[str]
    has_title_placeholder: bool
    has_body_placeholder: bool
    title_from_name: bool
    reasons: list[str]


def summarize_placeholders(placeholders: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate placeholder counts and area statistics."""
    if not placeholders:
        return {}

    counts: Counter[str] = Counter()
    processed: list[tuple[float, dict[str, Any]]] = []
    type_area: defaultdict[str, float] = defaultdict(float)
    total_area = 0.0

    for placeholder in placeholders:
        placeholder_type = str(placeholder.get("type") or "").casefold() or "unknown"
        counts[placeholder_type] += 1

        bbox = placeholder.get("bbox") or {}
        width = float(bbox.get("width") or 0.0)
        height = float(bbox.get("height") or 0.0)
        area = max(width, 0.0) * max(height, 0.0)
        total_area += area
        type_area[placeholder_type] += area

        flags = placeholder.get("flags")
        if isinstance(flags, list):
            flag_list = [str(flag) for flag in flags[:6]]
        else:
            flag_list = []

        entry: dict[str, Any] = {
            "name": str(placeholder.get("name") or "")[:64],
            "type": placeholder_type,
        }
        if flag_list:
            entry["flags"] = flag_list
        shape_type = placeholder.get("shape_type")
        if shape_type:
            entry["shape_type"] = str(shape_type).casefold()
        processed.append((area, entry))

    details: list[dict[str, Any]] = []
    for area, entry in sorted(processed, key=lambda item: item[0], reverse=True)[:8]:
        item = dict(entry)
        item["area_ratio"] = round(area / total_area, 3) if total_area > 0 else None
        details.append(item)

    area_ratio = {
        key: round(value / total_area, 3)
        for key, value in type_area.items()
        if total_area > 0
    }

    attributes = {
        "total": sum(counts.values()),
        "has_title": counts.get("title", 0) + counts.get("subtitle", 0) > 0,
        "has_body": counts.get("body", 0) + counts.get("content", 0) > 0,
        "has_table": counts.get("table", 0) > 0,
        "has_chart": counts.get("chart", 0) > 0,
        "has_visual": (
            counts.get("image", 0)
            + counts.get("media", 0)
            + counts.get("object", 0)
        )
        > 0,
    }

    return {
        "counts": {key: counts[key] for key in sorted(counts)},
        "area_ratio": area_ratio,
        "details": details,
        "attributes": attributes,
    }


def _classify_position(
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    slide_width: float,
    slide_height: float,
) -> PositionLabel:
    if slide_width <= 0 or slide_height <= 0:
        return ("中央", "中央")

    center_x = left + width / 2
    center_y = top + height / 2

    horizontal_ratio = center_x / slide_width if slide_width else 0.5
    vertical_ratio = center_y / slide_height if slide_height else 0.5

    if horizontal_ratio < 1 / 3:
        horizontal = "左側"
    elif horizontal_ratio > 2 / 3:
        horizontal = "右側"
    else:
        horizontal = "中央"

    if vertical_ratio < 1 / 3:
        vertical = "上部"
    elif vertical_ratio > 2 / 3:
        vertical = "下部"
    else:
        vertical = "中央"

    return (vertical, horizontal)


def _compose_position_label(position: PositionLabel) -> str:
    vertical, horizontal = position

    if vertical == "中央" and horizontal == "中央":
        return "中央"

    if vertical == "上部" and horizontal == "左側":
        return "左上"
    if vertical == "上部" and horizontal == "右側":
        return "右上"
    if vertical == "下部" and horizontal == "左側":
        return "左下"
    if vertical == "下部" and horizontal == "右側":
        return "右下"

    if horizontal == "中央":
        return f"{vertical}中央"
    if vertical == "中央":
        base = horizontal.replace("側", "寄り")
        return f"中央{base}"

    return f"{vertical}{horizontal}"


def _size_label(area_ratio: float | None) -> str | None:
    if area_ratio is None:
        return None
    if area_ratio >= 0.25:
        return "大きめの"
    if area_ratio >= 0.12:
        return "中程度の"
    if area_ratio >= 0.05:
        return "小さめの"
    if area_ratio > 0:
        return "コンパクトな"
    return None


def _placeholder_label(placeholder: dict[str, Any]) -> str:
    name = str(placeholder.get("name") or "")
    placeholder_type = str(placeholder.get("type") or "").casefold()
    lowered_name = name.casefold()

    if placeholder_type in {"title", "subtitle"}:
        return "サブタイトル枠" if placeholder_type == "subtitle" else "タイトル枠"
    if placeholder_type in {"body", "content", "text"}:
        return "本文枠"
    if placeholder_type == "table":
        return "表用プレースホルダー"
    if placeholder_type == "chart":
        return "チャート用プレースホルダー"
    if placeholder_type in {"image", "media"}:
        return "ビジュアル枠"
    if placeholder_type == "notes":
        return "ノート枠"
    if placeholder_type == "footer":
        return "ページ番号枠"

    if placeholder_type == "object":
        if any(keyword in lowered_name for keyword in ("logo", "mark", "brand")):
            return "ロゴ枠"
        if any(keyword in lowered_name for keyword in ("image", "photo", "visual")):
            return "ビジュアル枠"
        if any(keyword in lowered_name for keyword in ("table", "grid")):
            return "表用プレースホルダー"
        if any(keyword in lowered_name for keyword in ("chart", "graph")):
            return "チャート用プレースホルダー"
        if any(keyword in lowered_name for keyword in ("body", "content", "text")):
            return "本文枠"
        return "オブジェクト枠"

    return "コンテンツ枠" if placeholder_type else "プレースホルダー"


def generate_layout_description(
    layout_name: str,
    placeholders: Sequence[dict[str, Any]],
    slide_size_emu: tuple[int, int] | None,
) -> str:
    """Generate a human-readable Japanese description of a layout."""

    if not placeholders:
        target = layout_name or "このレイアウト"
        return f"{target} レイアウトはプレースホルダーが未定義です。"

    slide_width, slide_height = (slide_size_emu or (0, 0))
    slide_area = float(slide_width) * float(slide_height)
    counts: Counter[str] = Counter()

    for placeholder in placeholders:
        p_type = str(placeholder.get("type") or "").casefold() or "unknown"
        counts[p_type] += 1

    target = layout_name or "このレイアウト"
    total = len(placeholders)

    feature_labels: list[str] = []
    if counts.get("title") or counts.get("subtitle"):
        feature_labels.append("タイトル")
    if counts.get("body") or counts.get("content") or counts.get("text"):
        feature_labels.append("本文")
    if counts.get("table"):
        feature_labels.append("表")
    if counts.get("chart"):
        feature_labels.append("チャート")
    if counts.get("image") or counts.get("media") or counts.get("object"):
        feature_labels.append("ビジュアル")
    if counts.get("footer"):
        feature_labels.append("フッター")
    if counts.get("notes"):
        feature_labels.append("ノート")

    feature_labels = list(dict.fromkeys(feature_labels))
    if feature_labels:
        features_text = "、".join(feature_labels)
        summary = (
            f"{target} レイアウトは {features_text} を配置できる {total} 個のプレースホルダー構成です。"
        )
    else:
        summary = f"{target} レイアウトは {total} 個のプレースホルダーを備えています。"

    detail_segments: list[str] = []

    for placeholder in sorted(
        placeholders,
        key=lambda item: (
            -(
                float(item.get("bbox", {}).get("width") or 0.0)
                * float(item.get("bbox", {}).get("height") or 0.0)
            )
        ),
    ):
        bbox = placeholder.get("bbox") or {}
        left = float(bbox.get("x") or 0.0)
        top = float(bbox.get("y") or 0.0)
        width = float(bbox.get("width") or 0.0)
        height = float(bbox.get("height") or 0.0)
        area = width * height
        area_ratio = area / slide_area if slide_area > 0 else None

        position_label = _compose_position_label(
            _classify_position(
                left=left,
                top=top,
                width=width,
                height=height,
                slide_width=float(slide_width or 0.0),
                slide_height=float(slide_height or 0.0),
            )
        )

        size_label = _size_label(area_ratio)
        label = _placeholder_label(placeholder)
        name = str(placeholder.get("name") or "")

        segment = f"{position_label}に"
        if size_label:
            segment += f"{size_label}"
        segment += label
        if name and name != label:
            segment += f"（{name}）"
        detail_segments.append(segment)

    if detail_segments:
        details_text = "、".join(detail_segments) + "が配置されています。"
    else:
        details_text = ""

    description = summary
    if details_text:
        description = f"{summary} {details_text}"

    return description.strip()


PLACEHOLDER_TYPE_ALIASES: dict[str, str] = {
    "BODY": "body",
    "VERTICAL_BODY": "body",
    "TITLE": "title",
    "SUBTITLE": "subtitle",
    "CENTER_TITLE": "title",
    "TABLE": "table",
    "CHART": "chart",
    "PICTURE": "image",
    "CONTENT": "body",
    "TEXT": "body",
    "MEDIA_CLIP": "media",
    "OBJECT": "object",
    "FOOTER": "footer",
    "SLIDE_NUMBER": "footer",
    "DATE": "footer",
    "VERTICAL_TITLE": "title",
    "NOTES": "notes",
}


def normalise_placeholder_type(
    placeholder_type: str | None,
    shape_name: str | None,
) -> str:
    key = (placeholder_type or "").upper()
    if key in PLACEHOLDER_TYPE_ALIASES:
        return PLACEHOLDER_TYPE_ALIASES[key]
    guessed = _guess_type_from_name(shape_name)
    return guessed or "unknown"


def _guess_type_from_name(name: str | None) -> str | None:
    if not name:
        return None
    lowered = name.casefold()
    if "title" in lowered:
        return "title"
    if "sub" in lowered:
        return "subtitle"
    if "note" in lowered:
        return "notes"
    if "table" in lowered:
        return "table"
    if "chart" in lowered or "graph" in lowered:
        return "chart"
    if "image" in lowered or "picture" in lowered or "photo" in lowered:
        return "image"
    if "body" in lowered or "content" in lowered:
        return "body"
    return None


def derive_usage_tags(
    layout_name: str,
    placeholders: Iterable[dict[str, Any]],
) -> HeuristicUsageTagsResult:
    """Derive heuristic usage tags and reasoning from layout name and placeholders."""
    tags: set[str] = set()
    reasons: dict[str, str] = {}
    name = layout_name or ""
    name_cf = name.casefold()

    has_title_placeholder = False
    has_body_placeholder = False
    has_chart_placeholder = False
    has_table_placeholder = False
    has_image_placeholder = False

    def add_tag(tag: str, reason: str) -> None:
        if tag not in tags:
            tags.add(tag)
            reasons.setdefault(tag, reason)

    for placeholder in placeholders:
        p_type_raw = placeholder.get("type") or ""
        p_type = p_type_raw.casefold()
        placeholder_name_cf = (placeholder.get("name") or "").casefold()

        if p_type == "title":
            has_title_placeholder = True
            add_tag("title", "placeholder:type=title")
        elif p_type in {"body", "content", "text"}:
            has_body_placeholder = True
            add_tag("content", "placeholder:type=body")
        elif p_type == "chart":
            has_chart_placeholder = True
            add_tag("chart", "placeholder:type=chart")
        elif p_type == "table":
            has_table_placeholder = True
            add_tag("table", "placeholder:type=table")
        elif p_type == "image":
            has_image_placeholder = True
            add_tag("visual", "placeholder:type=image")
        elif p_type == "object":
            if any(keyword in placeholder_name_cf for keyword in ("body", "content", "text", "message")):
                has_body_placeholder = True
                add_tag("content", "placeholder:type=object(body)")
            elif any(keyword in placeholder_name_cf for keyword in ("logo", "image", "picture", "visual")):
                has_image_placeholder = True
                add_tag("visual", "placeholder:type=object(visual)")
            elif any(keyword in placeholder_name_cf for keyword in ("table", "grid")):
                has_table_placeholder = True
                add_tag("table", "placeholder:type=object(table)")
            elif any(keyword in placeholder_name_cf for keyword in ("chart", "graph")):
                has_chart_placeholder = True
                add_tag("chart", "placeholder:type=object(chart)")
        elif p_type == "media":
            if any(keyword in placeholder_name_cf for keyword in ("chart", "graph")):
                has_chart_placeholder = True
                add_tag("chart", "placeholder:type=media(chart)")
            elif any(keyword in placeholder_name_cf for keyword in ("table", "grid")):
                has_table_placeholder = True
                add_tag("table", "placeholder:type=media(table)")
            elif any(keyword in placeholder_name_cf for keyword in ("image", "picture", "photo", "visual")):
                has_image_placeholder = True
                add_tag("visual", "placeholder:type=media(image)")
        elif p_type == "notes":
            add_tag("notes", "placeholder:type=notes")
        elif p_type == "subtitle":
            has_title_placeholder = True
            add_tag("title", "placeholder:type=subtitle")
        elif p_type == "footer":
            add_tag("footer", "placeholder:type=footer")
        elif p_type == "unknown":
            if any(keyword in placeholder_name_cf for keyword in ("title", "header")):
                has_title_placeholder = True
                add_tag("title", "placeholder:name~title")
            elif any(keyword in placeholder_name_cf for keyword in ("body", "content", "message")):
                has_body_placeholder = True
                add_tag("content", "placeholder:name~body")
            elif any(keyword in placeholder_name_cf for keyword in ("chart", "graph")):
                has_chart_placeholder = True
                add_tag("chart", "placeholder:name~chart")
            elif any(keyword in placeholder_name_cf for keyword in ("table", "grid")):
                has_table_placeholder = True
                add_tag("table", "placeholder:name~table")
            elif any(keyword in placeholder_name_cf for keyword in ("image", "picture", "photo", "visual")):
                has_image_placeholder = True
                add_tag("visual", "placeholder:name~image")

    if has_chart_placeholder and "chart" not in tags:
        add_tag("chart", "placeholder:derived=chart")
    if has_table_placeholder and "table" not in tags:
        add_tag("table", "placeholder:derived=table")
    if has_image_placeholder and "visual" not in tags:
        add_tag("visual", "placeholder:derived=visual")

    if "agenda" in name_cf or "toc" in name_cf:
        add_tag("agenda", "name:contains=agenda")
    if "summary" in name_cf or "overview" in name_cf:
        add_tag("overview", "name:contains=overview")
    if "table" in name_cf:
        add_tag("table", "name:contains=table")
    if "chart" in name_cf:
        add_tag("chart", "name:contains=chart")

    def _looks_like_title_layout(layout_name: str, layout_name_cf: str) -> bool:
        if not layout_name:
            return False
        if any(keyword in layout_name_cf for keyword in ("cover", "front page")):
            return True
        if "title" in layout_name_cf and "content" not in layout_name_cf:
            return True
        if "タイトル" in layout_name and "コンテンツ" not in layout_name:
            return True
        if "表紙" in layout_name:
            return True
        if "セクション" in layout_name and ("タイトル" in layout_name or "表紙" in layout_name):
            return True
        return False

    title_from_name = _looks_like_title_layout(name, name_cf)
    if title_from_name:
        add_tag("title", "name:pattern=title")
    elif has_title_placeholder and not has_body_placeholder:
        add_tag("title", "placeholder:only_title")

    if has_body_placeholder:
        add_tag("content", "placeholder:has_body")

    reasons_list = [reasons[tag] for tag in sorted(reasons)]
    return HeuristicUsageTagsResult(
        tags=tags,
        has_title_placeholder=has_title_placeholder,
        has_body_placeholder=has_body_placeholder,
        title_from_name=title_from_name,
        reasons=reasons_list,
    )
