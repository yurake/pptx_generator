from __future__ import annotations

import json

from pptx_generator.prepare.source import PrepareSourceDocument


def test_parse_file_reads_json(tmp_path) -> None:
    payload = {
        "meta": {
            "title": "Sample",
            "prepare_id": "example",
            "client": "Example Corp",
        },
        "chapters": [],
    }
    target = tmp_path / "sample.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    document = PrepareSourceDocument.parse_file(target)

    assert document.meta.title == "Sample"
    assert document.meta.prepare_id == "example"


def test_parse_file_preserves_blank_lines_in_markdown(tmp_path) -> None:
    text = "\n".join(
        [
            "# Sample Title",
            "Intro line 1",
            "",
            "Intro line 2",
            "## Chapter One",
            "First detail",
            "",
            "Second detail",
            "- Support A",
            "- Support B",
            "",
        ]
    )
    target = tmp_path / "sample.md"
    target.write_text(text, encoding="utf-8")

    document = PrepareSourceDocument.parse_file(target)

    assert document.meta.title == "Sample Title"
    assert document.meta.objective == "Intro line 1\n\nIntro line 2"
    assert len(document.chapters) == 1
    chapter = document.chapters[0]
    assert chapter.title == "Chapter One"
    assert chapter.details == ["First detail", "", "Second detail"]
    assert [item.statement for item in chapter.supporting_points] == ["Support A", "Support B"]
