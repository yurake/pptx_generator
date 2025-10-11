from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.branding_extractor import (
    BrandingExtractionError,
    extract_branding_config,
)


SAMPLE_TEMPLATE = Path("samples/templates/templates.pptx")


@pytest.mark.skipif(not SAMPLE_TEMPLATE.exists(), reason="サンプルテンプレートが存在しない")
def test_extract_branding_config_from_sample_template() -> None:
    result = extract_branding_config(SAMPLE_TEMPLATE).as_dict()

    heading_font = result["fonts"]["heading"]
    body_font = result["fonts"]["body"]
    colors = result["colors"]
    footer = result["footer"]

    assert heading_font["name"] == "Meiryo UI"
    assert heading_font["size_pt"] == 24.0
    assert heading_font["color_hex"] == "#000000"

    assert body_font["name"] == "Meiryo UI"
    assert body_font["size_pt"] == 20.0
    assert body_font["color_hex"] == "#000000"

    assert colors == {
        "primary": "#156082",
        "secondary": "#E97132",
        "accent": "#196B24",
        "background": "#FFFFFF",
    }

    assert footer["text"] == ""
    assert footer["show_page_number"] is True


def test_extract_branding_config_missing_template(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pptx"
    with pytest.raises(BrandingExtractionError):
        extract_branding_config(missing)
