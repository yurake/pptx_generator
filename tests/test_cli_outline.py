import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pptx_generator.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture()
def sample_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "spec.json"
    _write_json(
        spec_path,
        {
            "meta": {
                "schema_version": "1.1",
                "title": "Test Spec",
                "client": "Test",
                "locale": "ja-JP"
            },
            "auth": {"created_by": "tester"},
            "slides": [
                {
                    "id": "s01",
                    "layout": "overview",
                    "title": "Overview",
                    "bullets": [
                        {
                            "anchor": None,
                            "items": [
                                {"id": "b1", "text": "Line 1", "level": 0},
                                {"id": "b2", "text": "Line 2", "level": 0}
                            ]
                        }
                    ]
                }
            ],
        },
    )
    return spec_path


@pytest.fixture()
def content_approved(tmp_path: Path) -> Path:
    content_path = tmp_path / "approved.json"
    _write_json(
        content_path,
        {
            "slides": [
                {
                    "id": "s01",
                    "layout": "overview",
                    "intent": "overview",
                    "type_hint": "overview",
                    "elements": {
                        "title": "Overview",
                        "body": ["Line 1", "Line 2"],
                        "table_data": None,
                        "note": None
                    },
                    "status": "approved",
                }
            ]
        },
    )
    return content_path


@pytest.fixture()
def layouts_file(tmp_path: Path) -> Path:
    layouts = tmp_path / "layouts.jsonl"
    layouts.write_text(
        json.dumps(
            {
                "layout_id": "overview__one_col",
                "usage_tags": ["overview"],
                "text_hint": {"max_lines": 5},
                "media_hint": {"allow_table": True},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return layouts


def test_outline_with_layout_reasons(
    runner: CliRunner,
    sample_spec: Path,
    content_approved: Path,
    layouts_file: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "draft"
    result = runner.invoke(
        app,
        [
            "outline",
            str(sample_spec),
            "--content-approved",
            str(content_approved),
            "--layouts",
            str(layouts_file),
            "--output",
            str(output_dir),
            "--chapter-template",
            "bp-report-2025",
            "--show-layout-reasons",
        ],
    )

    assert result.exit_code == 0, result.output
    draft_path = output_dir / "draft_draft.json"
    assert draft_path.exists()
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    slide = draft["sections"][0]["slides"][0]
    assert "layout_score_detail" in slide
    assert slide["layout_score_detail"]["uses_tag"] > 0
