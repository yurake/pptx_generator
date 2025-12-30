from __future__ import annotations

import xml.etree.ElementTree as ET

from pptx_generator.branding_extractor import SCHEME_COLOR_TAG, _color_from_def, _resolve_background_color

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def test_scheme_color_tag_is_used_in_color_from_def():
    element = ET.fromstring(
        f"""
        <a:defRPr xmlns:a="{NS['a']}">
          <a:solidFill>
            <{SCHEME_COLOR_TAG} val="accent1" />
          </a:solidFill>
        </a:defRPr>
        """
    )
    color = _color_from_def(element, {"accent1": "a1b2c3"}, {})
    assert color == "#A1B2C3"


def test_resolve_background_color_uses_scheme_tag():
    element = ET.fromstring(
        f"""
        <p:sldMaster xmlns:a="{NS['a']}" xmlns:p="{NS['p']}">
          <p:bgRef>
            <{SCHEME_COLOR_TAG} val="bg1" />
          </p:bgRef>
        </p:sldMaster>
        """
    )
    color = _resolve_background_color(element, {"bg1": "112233"}, {})
    assert color == "#112233"
