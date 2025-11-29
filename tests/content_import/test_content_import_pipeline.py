from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.content_import import ContentImportError, ContentImportService


def test_import_from_text_file(tmp_path: Path) -> None:
    source = tmp_path / "draft.txt"
    source.write_text("# 背景\n- 課題A\n- 課題B\n\n# 提案\n提案内容を整理", encoding="utf-8")

    service = ContentImportService()
    result = service.import_sources([str(source)])

    assert result.document.slides
    assert result.document.slides[0].status == "draft"
    assert result.document.slides[0].elements.title == "背景"
    assert result.document.slides[0].elements.body
    assert result.meta["total_slides"] == len(result.document.slides)
    assert not result.warnings


def test_import_from_data_uri() -> None:
    data_uri = "data:text/plain;charset=utf-8,%23%20タイトル%0A本文ライン"

    service = ContentImportService()
    result = service.import_sources([data_uri])

    slide = result.document.slides[0]
    assert slide.elements.title.startswith("タイトル")
    assert slide.elements.body[0]


def test_import_without_sources_raises() -> None:
    service = ContentImportService()
    with pytest.raises(ContentImportError):
        service.import_sources([])
