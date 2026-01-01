from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.cli_hooks.template_id import (
    TemplateIdExtractionError,
    extract_template_id_from_json_file,
)


def test_extract_template_id_from_json_file_finds_nested_meta(tmp_path: Path) -> None:
    payload = {"meta": {"template_id": "demo_meta"}}
    target = tmp_path / "spec.json"
    target.write_text('{"meta":{"template_id":"demo_meta"}}', encoding="utf-8")

    template_id = extract_template_id_from_json_file(target, strict=True)

    assert template_id == "demo_meta"


def test_extract_template_id_from_json_file_top_level(tmp_path: Path) -> None:
    target = tmp_path / "spec.json"
    target.write_text('{"template_id":"top_level","meta":{"template_id":"meta_tpl"}}', encoding="utf-8")

    template_id = extract_template_id_from_json_file(target, strict=True)

    assert template_id == "top_level"


def test_extract_template_id_from_json_file_finds_template_style(tmp_path: Path) -> None:
    target = tmp_path / "spec.json"
    target.write_text('{"template_style":{"template_id":"style_tpl"}}', encoding="utf-8")

    template_id = extract_template_id_from_json_file(target, strict=True)

    assert template_id == "style_tpl"


def test_extract_template_id_from_json_file_missing_raises_when_strict(tmp_path: Path) -> None:
    target = tmp_path / "spec.json"
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(TemplateIdExtractionError):
        extract_template_id_from_json_file(target, strict=True, require_id=True)


def test_extract_template_id_prefers_top_level_over_meta_or_style(tmp_path: Path) -> None:
    target = tmp_path / "spec.json"
    target.write_text(
        '{"template_id":"top","meta":{"template_id":"meta_tpl"},"template_style":{"template_id":"style_tpl"}}',
        encoding="utf-8",
    )

    template_id = extract_template_id_from_json_file(target, strict=True)

    assert template_id == "top"


def test_extract_template_id_from_json_file_invalid_json_strict(tmp_path: Path) -> None:
    target = tmp_path / "spec.json"
    target.write_text("{invalid", encoding="utf-8")

    with pytest.raises(TemplateIdExtractionError):
        extract_template_id_from_json_file(target, strict=True)


def test_extract_template_id_from_json_file_missing_file_non_strict_returns_none(tmp_path: Path) -> None:
    target = tmp_path / "missing.json"

    assert extract_template_id_from_json_file(target, strict=False) is None


def test_template_id_extraction_error_format(tmp_path: Path) -> None:
    exc = TemplateIdExtractionError(path=tmp_path / "missing.json", reason="fail")

    assert "missing.json" in exc.format_user_message()
    assert "fail" in exc.format_user_message()
