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
    text = 
