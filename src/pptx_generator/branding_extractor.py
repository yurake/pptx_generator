"""PPTX テンプレートからブランド設定を抽出するユーティリティ。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from .settings import BrandingConfig, BrandingFont

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


class BrandingExtractionError(Exception):
    """テンプレートからブランド情報を取得できない場合に送出する例外。"""


@dataclass(slots=True)
class BrandingExtractionResult:
    fonts: dict[str, Any]
    colors: dict[str, str]
    footer: dict[str, Any]
    source: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "fonts": self.fonts,
            "colors": self.colors,
            "footer": self.footer,
            "source": self.source,
        }

    def to_branding_config(self, fallback: BrandingConfig | None = None) -> BrandingConfig:
        """抽出結果を ``BrandingConfig`` に変換する。"""

        defaults = fallback or BrandingConfig.default()

        heading_raw = self.fonts.get("heading", {})
        body_raw = self.fonts.get("body", {})

        heading_font = BrandingFont(
            name=_pick_str(heading_raw.get("name")) or defaults.heading_font.name,
            size_pt=_pick_float(heading_raw.get("size_pt"))
            or defaults.heading_font.size_pt,
            color_hex=_format_hex(heading_raw.get("color_hex"))
            if heading_raw.get("color_hex")
            else defaults.heading_font.color_hex,
        )

        body_font = BrandingFont(
            name=_pick_str(body_raw.get("name")) or defaults.body_font.name,
            size_pt=_pick_float(body_raw.get("size_pt"))
            or defaults.body_font.size_pt,
            color_hex=_format_hex(body_raw.get("color_hex"))
            if body_raw.get("color_hex")
            else defaults.body_font.color_hex,
        )

        return BrandingConfig(
            heading_font=heading_font,
            body_font=body_font,
            primary_color=_format_hex(self.colors.get("primary"))
            if self.colors.get("primary")
            else defaults.primary_color,
            secondary_color=_format_hex(self.colors.get("secondary"))
            if self.colors.get("secondary")
            else defaults.secondary_color,
            accent_color=_format_hex(self.colors.get("accent"))
            if self.colors.get("accent")
            else defaults.accent_color,
            background_color=_format_hex(self.colors.get("background"))
            if self.colors.get("background")
            else defaults.background_color,
        )

    def to_branding_payload(self, fallback: BrandingConfig | None = None) -> dict[str, Any]:
        """branding.json 互換のペイロードを返す。"""

        config = self.to_branding_config(fallback)
        payload = {
            "fonts": {
                "heading": {
                    "name": config.heading_font.name,
                    "size_pt": config.heading_font.size_pt,
                    "color_hex": config.heading_font.color_hex,
                },
                "body": {
                    "name": config.body_font.name,
                    "size_pt": config.body_font.size_pt,
                    "color_hex": config.body_font.color_hex,
                },
            },
            "colors": {
                "primary": config.primary_color,
                "secondary": config.secondary_color,
                "accent": config.accent_color,
                "background": config.background_color,
            },
        }

        if self.footer:
            payload["footer"] = self.footer

        return payload


def extract_branding_config(template_path: Path) -> BrandingExtractionResult:
    """テンプレートからブランド設定相当の情報を抽出して返す。"""

    if not template_path.exists():
        raise BrandingExtractionError(f"テンプレートが見つかりません: {template_path}")

    try:
        with ZipFile(template_path) as archive:
            theme_root = _load_xml(archive, "ppt/theme/theme1.xml")
            master_root = _load_xml(archive, "ppt/slideMasters/slideMaster1.xml")
    except KeyError as exc:  # 指定パスが存在しない場合
        raise BrandingExtractionError("テンプレート内のテーマまたはスライドマスターを取得できませんでした") from exc

    theme_colors = _extract_theme_colors(theme_root)
    theme_fonts = _extract_theme_fonts(theme_root)

    color_map = _extract_color_map(master_root)

    heading_style = master_root.find(".//p:txStyles/p:titleStyle/a:lvl1pPr/a:defRPr", NS)
    body_style = master_root.find(".//p:txStyles/p:bodyStyle/a:lvl1pPr/a:defRPr", NS)

    heading_font = {
        "name": _font_name_from_def(heading_style) or theme_fonts.get("heading") or "",
        "size_pt": _size_from_def(heading_style) or 0.0,
        "color_hex": _color_from_def(heading_style, theme_colors, color_map)
        or theme_colors.get("dk1")
        or "#000000",
    }

    body_font = {
        "name": _font_name_from_def(body_style) or theme_fonts.get("body") or "",
        "size_pt": _size_from_def(body_style) or 0.0,
        "color_hex": _color_from_def(body_style, theme_colors, color_map)
        or heading_font["color_hex"],
    }

    colors = {
        "primary": _format_hex(theme_colors.get("accent1")),
        "secondary": _format_hex(theme_colors.get("accent2")),
        "accent": _format_hex(theme_colors.get("accent3")),
        "background": _resolve_background_color(master_root, theme_colors, color_map),
    }

    footer_text = _extract_footer_text(master_root)
    show_page_number = _has_page_number_placeholder(master_root)

    footer = {
        "text": footer_text,
        "show_page_number": show_page_number,
    }

    source = {
        "template": str(template_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return BrandingExtractionResult(
        fonts={"heading": heading_font, "body": body_font},
        colors=colors,
        footer=footer,
        source=source,
    )


def _load_xml(archive: ZipFile, internal_path: str) -> ET.Element:
    return ET.fromstring(archive.read(internal_path))


def _extract_theme_fonts(theme_root: ET.Element) -> dict[str, str]:
    major_font = theme_root.find(".//a:fontScheme/a:majorFont", NS)
    minor_font = theme_root.find(".//a:fontScheme/a:minorFont", NS)
    return {
        "heading": _font_name_from_theme(major_font) or "",
        "body": _font_name_from_theme(minor_font) or "",
    }


def _extract_theme_colors(theme_root: ET.Element) -> dict[str, str]:
    colors: dict[str, str] = {}
    clr_scheme = theme_root.find(".//a:clrScheme", NS)
    if clr_scheme is None:
        return colors
    for child in list(clr_scheme):
        name = child.tag.split("}")[-1]
        colors[name] = _color_value(child)
    return colors


def _extract_color_map(master_root: ET.Element) -> dict[str, str]:
    color_map_elem = master_root.find(".//p:clrMap", NS)
    if color_map_elem is None:
        return {}
    return dict(color_map_elem.attrib)


def _font_name_from_theme(font_elem: ET.Element | None) -> str | None:
    if font_elem is None:
        return None
    for tag in ("a:latin", "a:ea", "a:cs"):
        child = font_elem.find(tag, NS)
        if child is not None and child.get("typeface"):
            return child.get("typeface")
    return None


def _font_name_from_def(def_rpr: ET.Element | None) -> str | None:
    if def_rpr is None:
        return None
    for tag in ("a:latin", "a:ea", "a:cs"):
        child = def_rpr.find(tag, NS)
        if child is not None and child.get("typeface"):
            return child.get("typeface")
    return None


def _size_from_def(def_rpr: ET.Element | None) -> float | None:
    if def_rpr is None:
        return None
    size_raw = def_rpr.get("sz")
    if not size_raw:
        return None
    try:
        return round(int(size_raw) / 100, 2)
    except ValueError:
        return None


def _color_from_def(
    def_rpr: ET.Element | None,
    theme_colors: dict[str, str],
    color_map: dict[str, str],
) -> str | None:
    if def_rpr is None:
        return None
    solid = def_rpr.find("a:solidFill", NS)
    if solid is None:
        return None
    rgb = solid.find("a:srgbClr", NS)
    if rgb is not None and rgb.get("val"):
        return _format_hex(rgb.get("val"))

    scheme = solid.find("a:schemeClr", NS)
    if scheme is None or scheme.get("val") is None:
        return None

    base_name = scheme.get("val")
    mapped_name = color_map.get(base_name, base_name)
    base_hex = theme_colors.get(mapped_name)
    if not base_hex:
        return None

    color = _format_hex(base_hex)
    modifiers = list(scheme)
    if modifiers:
        color = _apply_color_modifiers(color, modifiers)
    return color


def _resolve_background_color(
    master_root: ET.Element,
    theme_colors: dict[str, str],
    color_map: dict[str, str],
) -> str:
    bg_ref = master_root.find(".//p:bgRef", NS)
    if bg_ref is not None:
        scheme = bg_ref.find("a:schemeClr", NS)
        if scheme is not None and scheme.get("val"):
            base = color_map.get(scheme.get("val"), scheme.get("val"))
            hex_value = theme_colors.get(base)
            if hex_value:
                return _format_hex(hex_value)

    bg = master_root.find(".//p:bg", NS)
    if bg is not None:
        solid = bg.find(".//a:srgbClr", NS)
        if solid is not None and solid.get("val"):
            return _format_hex(solid.get("val"))
        scheme = bg.find(".//a:schemeClr", NS)
        if scheme is not None and scheme.get("val"):
            base = color_map.get(scheme.get("val"), scheme.get("val"))
            hex_value = theme_colors.get(base)
            if hex_value:
                return _format_hex(hex_value)

    return "#FFFFFF"


def _extract_footer_text(master_root: ET.Element) -> str:
    for sp in master_root.findall(".//p:sp", NS):
        placeholder = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if placeholder is not None and placeholder.get("type") == "ftr":
            texts = [t.text or "" for t in sp.findall(".//a:t", NS)]
            return "".join(texts).strip()
    return ""


def _has_page_number_placeholder(master_root: ET.Element) -> bool:
    for sp in master_root.findall(".//p:sp", NS):
        placeholder = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if placeholder is not None and placeholder.get("type") == "sldNum":
            return True
    return False


def _color_value(node: ET.Element) -> str:
    srgb = node.find("a:srgbClr", NS)
    if srgb is not None and srgb.get("val"):
        return srgb.get("val")
    scheme = node.find("a:schemeClr", NS)
    if scheme is not None and scheme.get("val"):
        return scheme.get("val")
    sys_clr = node.find("a:sysClr", NS)
    if sys_clr is not None and sys_clr.get("lastClr"):
        return sys_clr.get("lastClr")
    return ""


def _format_hex(value: str | None) -> str:
    if not value:
        return "#000000"
    stripped = value.strip().lstrip("#")
    return f"#{stripped.upper()}"


def _pick_str(value: object | None) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _pick_float(value: object | None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        if isinstance(value, str) and value.strip():
            return float(value)
    except ValueError:
        return None
    return None


def _apply_color_modifiers(color_hex: str, modifiers: list[ET.Element]) -> str:
    r, g, b = _hex_to_rgb(color_hex)
    for modifier in modifiers:
        tag = modifier.tag.split("}")[-1]
        value = modifier.get("val")
        if value is None:
            continue
        amount = int(value)
        if tag == "tint":
            r, g, b = (_apply_tint_channel(r, amount), _apply_tint_channel(g, amount), _apply_tint_channel(b, amount))
        elif tag == "shade":
            r, g, b = (_apply_shade_channel(r, amount), _apply_shade_channel(g, amount), _apply_shade_channel(b, amount))
        elif tag == "lumMod":
            r, g, b = (_apply_lum_mod_channel(r, amount), _apply_lum_mod_channel(g, amount), _apply_lum_mod_channel(b, amount))
        elif tag == "lumOff":
            r, g, b = (_apply_lum_off_channel(r, amount), _apply_lum_off_channel(g, amount), _apply_lum_off_channel(b, amount))
    return _rgb_to_hex(r, g, b)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    stripped = value.lstrip("#")
    return tuple(int(stripped[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _apply_tint_channel(channel: int, amount: int) -> int:
    return min(255, round(channel + (255 - channel) * amount / 100000))


def _apply_shade_channel(channel: int, amount: int) -> int:
    return max(0, round(channel * (100000 - amount) / 100000))


def _apply_lum_mod_channel(channel: int, amount: int) -> int:
    return max(0, min(255, round(channel * amount / 100000)))


def _apply_lum_off_channel(channel: int, amount: int) -> int:
    return max(0, min(255, round(channel + 255 * amount / 100000)))
