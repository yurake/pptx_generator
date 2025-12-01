"""Utilities for layout placeholder summarisation and heuristic usage tag derivation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence
from collections import Counter, defaultdict

PositionLabel = tuple[str, str]

CONTENT_LIKE_PLACEHOLDER_TYPES = {
    "title",
    "subtitle",
    "body",
    "content",
    "text",
    "table",
    "chart",
    "image",
    "media",
    "object",
}

TEXT_INPUT_PLACEHOLDER_TYPES = {
    "title",
    "subtitle",
    "body",
    "content",
    "text",
    "table",
    "notes",
}


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


def _size_label(placeholder: dict[str, Any], area_ratio: float | None) -> str | None:
    if area_ratio is None:
        return None
    placeholder_type = str(placeholder.get("type") or "").casefold()
    is_content_placeholder = placeholder_type in CONTENT_LIKE_PLACEHOLDER_TYPES
    if is_content_placeholder:
        if area_ratio >= 0.25:
            return "大きめの"
        if area_ratio >= 0.12:
            return "中程度の"
        if area_ratio >= 0.05:
            return "小さめの"
        if area_ratio > 0:
            return "コンパクトな"
        return None

    # 非コンテンツ要素（ロゴや装飾など）はサイズに応じて装飾用途として明示する
    if area_ratio >= 0.12:
        return "大きめの装飾用の"
    if area_ratio >= 0.05:
        return "装飾用の"
    if area_ratio > 0:
        return "小さな装飾用の"
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


def _expects_text_input(placeholder: dict[str, Any]) -> bool:
    placeholder_type = str(placeholder.get("type") or "").casefold()
    if placeholder_type in TEXT_INPUT_PLACEHOLDER_TYPES:
        return True
    lowered_name = str(placeholder.get("name") or "").casefold()
    if placeholder_type == "object":
        if any(keyword in lowered_name for keyword in ("body", "content", "text")):
            return True
    if placeholder_type == "unknown":
        if any(keyword in lowered_name for keyword in ("title", "subtitle", "body", "content", "text")):
            return True
    return False


def _count_placeholder_types(placeholders: Sequence[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for placeholder in placeholders:
        placeholder_type = str(placeholder.get("type") or "").casefold() or "unknown"
        counts[placeholder_type] += 1
    return counts


def _feature_labels_from_counts(counts: Counter[str]) -> list[str]:
    labels: list[str] = []
    if counts.get("title") or counts.get("subtitle"):
        labels.append("タイトル")
    if counts.get("body") or counts.get("content") or counts.get("text"):
        labels.append("本文")
    if counts.get("table"):
        labels.append("表")
    if counts.get("chart"):
        labels.append("チャート")
    if counts.get("image") or counts.get("media") or counts.get("object"):
        labels.append("ビジュアル")
    if counts.get("footer"):
        labels.append("フッター")
    if counts.get("notes"):
        labels.append("ノート")
    return list(dict.fromkeys(labels))


def _compose_overview_text(target: str, total: int, feature_labels: Sequence[str]) -> str:
    if feature_labels:
        features_text = "、".join(feature_labels)
        return f"{target} レイアウトは {features_text} を配置できる {total} 個のプレースホルダー構成です。"
    return f"{target} レイアウトは {total} 個のプレースホルダーを備えています。"


def _sorted_placeholders_for_description(placeholders: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        placeholders,
        key=lambda item: -(
            float(item.get("bbox", {}).get("width") or 0.0)
            * float(item.get("bbox", {}).get("height") or 0.0)
        ),
    )


def _placeholder_area_metrics(
    placeholder: dict[str, Any],
    slide_area: float,
) -> tuple[float, float, float | None]:
    bbox = placeholder.get("bbox") or {}
    width = float(bbox.get("width") or 0.0)
    height = float(bbox.get("height") or 0.0)
    area = width * height
    return width, height, area / slide_area if slide_area > 0 else None


def _build_element_entry(
    placeholder: dict[str, Any],
    *,
    slide_width: float,
    slide_height: float,
    slide_area: float,
) -> dict[str, Any]:
    bbox = placeholder.get("bbox") or {}
    left = float(bbox.get("x") or 0.0)
    top = float(bbox.get("y") or 0.0)
    width = float(bbox.get("width") or 0.0)
    height = float(bbox.get("height") or 0.0)
    _, _, area_ratio = _placeholder_area_metrics(placeholder, slide_area)

    position_label = _compose_position_label(
        _classify_position(
            left=left,
            top=top,
            width=width,
            height=height,
            slide_width=slide_width,
            slide_height=slide_height,
        )
    )

    size_label = _size_label(placeholder, area_ratio)
    label = _placeholder_label(placeholder)
    name = str(placeholder.get("name") or "")
    expects_text = _expects_text_input(placeholder)

    segment = f"{position_label}に"
    if size_label:
        segment += f"{size_label}"
    segment += label
    if name and name != label:
        segment += f"（{name}）"
    if not expects_text:
        segment += "（テキスト入力非想定）"

    size_keyword = None
    if size_label:
        size_keyword = size_label[:-1] if size_label.endswith("の") else size_label

    element_entry: dict[str, Any] = {
        "anchor": name or None,
        "type": str(placeholder.get("type") or "").lower() or None,
        "role": label,
        "position": position_label,
        "size_label": size_keyword,
        "expects_text": expects_text,
        "description": segment,
    }
    if area_ratio is not None:
        element_entry["area_ratio"] = round(area_ratio, 3)

    flags = placeholder.get("flags")
    if isinstance(flags, list) and flags:
        element_entry["flags"] = list(flags)
    return element_entry


def generate_layout_description(
    layout_name: str,
    placeholders: Sequence[dict[str, Any]],
    slide_size_emu: tuple[int, int] | None,
) -> dict[str, Any]:
    """Generate structured overview and element descriptions for a layout."""

    target = layout_name or "このレイアウト"
    if not placeholders:
        return {
            "overview": f"{target} レイアウトはプレースホルダーが未定義です。",
            "elements": [],
        }

    slide_width, slide_height = (slide_size_emu or (0, 0))
    slide_area = float(slide_width) * float(slide_height)
    counts = _count_placeholder_types(placeholders)
    feature_labels = _feature_labels_from_counts(counts)
    overview = _compose_overview_text(target, len(placeholders), feature_labels)

    elements = [
        _build_element_entry(
            placeholder,
            slide_width=float(slide_width or 0.0),
            slide_height=float(slide_height or 0.0),
            slide_area=slide_area,
        )
        for placeholder in _sorted_placeholders_for_description(placeholders)[:20]
    ]

    return {
        "overview": overview,
        "elements": elements,
    }


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


_DIRECT_PLACEHOLDER_RULES: dict[str, tuple[str, tuple[str, ...]]] = {
    "title": ("mark_title", ("placeholder:type=title",)),
    "subtitle": ("mark_title", ("placeholder:type=subtitle",)),
    "body": ("mark_body", ("placeholder:type=body",)),
    "content": ("mark_body", ("placeholder:type=body",)),
    "text": ("mark_body", ("placeholder:type=body",)),
    "chart": ("mark_chart", ("placeholder:type=chart",)),
    "table": ("mark_table", ("placeholder:type=table",)),
    "image": ("mark_image", ("placeholder:type=image",)),
    "notes": ("add_tag_only", ("notes", "placeholder:type=notes")),
    "footer": ("add_tag_only", ("footer", "placeholder:type=footer")),
}

_OBJECT_BODY_KEYWORDS = ("body", "content", "text", "message")
_OBJECT_IMAGE_KEYWORDS = ("logo", "image", "picture", "visual")
_OBJECT_TABLE_KEYWORDS = ("table", "grid")
_OBJECT_CHART_KEYWORDS = ("chart", "graph")

_MEDIA_CHART_KEYWORDS = ("chart", "graph")
_MEDIA_TABLE_KEYWORDS = ("table", "grid")
_MEDIA_IMAGE_KEYWORDS = ("image", "picture", "photo", "visual")

_UNKNOWN_TITLE_KEYWORDS = ("title", "header")
_UNKNOWN_BODY_KEYWORDS = ("body", "content", "message")
_UNKNOWN_CHART_KEYWORDS = ("chart", "graph")
_UNKNOWN_TABLE_KEYWORDS = ("table", "grid")
_UNKNOWN_IMAGE_KEYWORDS = ("image", "picture", "photo", "visual")


@dataclass(slots=True)
class _UsageTagState:
    tags: set[str] = field(default_factory=set)
    reasons: dict[str, str] = field(default_factory=dict)
    has_title_placeholder: bool = False
    has_body_placeholder: bool = False
    has_chart_placeholder: bool = False
    has_table_placeholder: bool = False
    has_image_placeholder: bool = False

    def add_tag(self, tag: str, reason: str) -> None:
        if tag not in self.tags:
            self.tags.add(tag)
            self.reasons.setdefault(tag, reason)

    def add_tag_only(self, tag: str, reason: str) -> None:
        self.add_tag(tag, reason)

    def mark_title(self, reason: str) -> None:
        self.has_title_placeholder = True
        self.add_tag("title", reason)

    def mark_body(self, reason: str) -> None:
        self.has_body_placeholder = True
        self.add_tag("content", reason)

    def mark_chart(self, reason: str) -> None:
        self.has_chart_placeholder = True
        self.add_tag("chart", reason)

    def mark_table(self, reason: str) -> None:
        self.has_table_placeholder = True
        self.add_tag("table", reason)

    def mark_image(self, reason: str) -> None:
        self.has_image_placeholder = True
        self.add_tag("visual", reason)

    def process_placeholder(self, placeholder: dict[str, Any]) -> None:
        p_type = str(placeholder.get("type") or "").casefold()
        handler = _DIRECT_PLACEHOLDER_RULES.get(p_type)
        if handler is not None:
            method_name, args = handler
            getattr(self, method_name)(*args)
            return

        name_cf = (placeholder.get("name") or "").casefold()
        if p_type == "object":
            self._handle_object_placeholder(name_cf)
        elif p_type == "media":
            self._handle_media_placeholder(name_cf)
        elif p_type == "unknown":
            self._handle_unknown_placeholder(name_cf)

    def _handle_object_placeholder(self, name_cf: str) -> None:
        if any(keyword in name_cf for keyword in _OBJECT_BODY_KEYWORDS):
            self.mark_body("placeholder:type=object(body)")
        elif any(keyword in name_cf for keyword in _OBJECT_IMAGE_KEYWORDS):
            self.mark_image("placeholder:type=object(visual)")
        elif any(keyword in name_cf for keyword in _OBJECT_TABLE_KEYWORDS):
            self.mark_table("placeholder:type=object(table)")
        elif any(keyword in name_cf for keyword in _OBJECT_CHART_KEYWORDS):
            self.mark_chart("placeholder:type=object(chart)")

    def _handle_media_placeholder(self, name_cf: str) -> None:
        if any(keyword in name_cf for keyword in _MEDIA_CHART_KEYWORDS):
            self.mark_chart("placeholder:type=media(chart)")
        elif any(keyword in name_cf for keyword in _MEDIA_TABLE_KEYWORDS):
            self.mark_table("placeholder:type=media(table)")
        elif any(keyword in name_cf for keyword in _MEDIA_IMAGE_KEYWORDS):
            self.mark_image("placeholder:type=media(image)")

    def _handle_unknown_placeholder(self, name_cf: str) -> None:
        if any(keyword in name_cf for keyword in _UNKNOWN_TITLE_KEYWORDS):
            self.mark_title("placeholder:name~title")
        elif any(keyword in name_cf for keyword in _UNKNOWN_BODY_KEYWORDS):
            self.mark_body("placeholder:name~body")
        elif any(keyword in name_cf for keyword in _UNKNOWN_CHART_KEYWORDS):
            self.mark_chart("placeholder:name~chart")
        elif any(keyword in name_cf for keyword in _UNKNOWN_TABLE_KEYWORDS):
            self.mark_table("placeholder:name~table")
        elif any(keyword in name_cf for keyword in _UNKNOWN_IMAGE_KEYWORDS):
            self.mark_image("placeholder:name~image")

    def ensure_derived_tags(self) -> None:
        if self.has_chart_placeholder:
            self.add_tag("chart", "placeholder:derived=chart")
        if self.has_table_placeholder:
            self.add_tag("table", "placeholder:derived=table")
        if self.has_image_placeholder:
            self.add_tag("visual", "placeholder:derived=visual")

    def ensure_body_tag(self) -> None:
        if self.has_body_placeholder:
            self.add_tag("content", "placeholder:has_body")


def _apply_layout_name_hints(state: _UsageTagState, layout_name: str) -> bool:
    name = layout_name or ""
    name_cf = name.casefold()
    if "agenda" in name_cf or "toc" in name_cf:
        state.add_tag("agenda", "name:contains=agenda")
    if "summary" in name_cf or "overview" in name_cf:
        state.add_tag("overview", "name:contains=overview")
    if "table" in name_cf:
        state.add_tag("table", "name:contains=table")
    if "chart" in name_cf:
        state.add_tag("chart", "name:contains=chart")

    title_from_name = _looks_like_title_layout(name, name_cf)
    if title_from_name:
        state.add_tag("title", "name:pattern=title")
    elif state.has_title_placeholder and not state.has_body_placeholder:
        state.add_tag("title", "placeholder:only_title")
    return title_from_name


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


def derive_usage_tags(
    layout_name: str,
    placeholders: Iterable[dict[str, Any]],
) -> HeuristicUsageTagsResult:
    """Derive heuristic usage tags and reasoning from layout name and placeholders."""
    state = _UsageTagState()
    for placeholder in placeholders:
        state.process_placeholder(placeholder)

    state.ensure_derived_tags()
    title_from_name = _apply_layout_name_hints(state, layout_name)
    state.ensure_body_tag()

    reasons_list = [state.reasons[tag] for tag in sorted(state.reasons)]
    return HeuristicUsageTagsResult(
        tags=set(state.tags),
        has_title_placeholder=state.has_title_placeholder,
        has_body_placeholder=state.has_body_placeholder,
        title_from_name=title_from_name,
        reasons=reasons_list,
    )
