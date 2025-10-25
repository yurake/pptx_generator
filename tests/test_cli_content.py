from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import app


SAMPLE_SPEC = Path("samples/json/sample_spec.json")
SAMPLE_CONTENT = Path("samples/json/sample_content_approved.json")
SAMPLE_REVIEW = Path("samples/json/sample_content_review_log.json")


def test_content_approve_outputs(tmp_path) -> None:
    output_dir = tmp_path / "content"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "content",
            str(SAMPLE_SPEC),
            "--content-approved",
            str(SAMPLE_CONTENT),
            "--content-review-log",
            str(SAMPLE_REVIEW),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    spec_output = output_dir / "spec_content_applied.json"
    assert spec_output.exists()
    spec_payload = json.loads(spec_output.read_text(encoding="utf-8"))
    agenda_slide = next(slide for slide in spec_payload["slides"] if slide["id"] == "agenda")
    body_texts = [item["text"] for group in agenda_slide.get("bullets", []) for item in group.get("items", [])]
    assert "背景整理（承認済み）" in body_texts

    content_output = output_dir / "content_approved.json"
    assert content_output.exists()

    meta_output = output_dir / "content_meta.json"
    assert meta_output.exists()
    meta_payload = json.loads(meta_output.read_text(encoding="utf-8"))
    assert meta_payload["content_approved"]["slides"] == 3
    assert meta_payload["spec"]["slides"] >= 3
    assert meta_payload["content_review_log"]["events"] > 0


def test_content_approve_rejects_unapproved_cards(tmp_path) -> None:
    invalid_content = tmp_path / "content_invalid.json"
    payload = {
        "slides": [
            {
                "id": "agenda",
                "status": "draft",
                "elements": {"title": "Draft"},
            }
        ]
    }
    invalid_content.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output_dir = tmp_path / "invalid"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "content",
            str(SAMPLE_SPEC),
            "--content-approved",
            str(invalid_content),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 4
    assert "検証に失敗" in result.output
    assert not (output_dir / "spec_content_applied.json").exists()


def test_content_import_generates_draft(tmp_path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("# インポート\n内容を記述", encoding="utf-8")

    output_dir = tmp_path / "draft"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "content",
            str(SAMPLE_SPEC),
            "--content-source",
            str(source),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    draft_path = output_dir / "content_draft.json"
    meta_path = output_dir / "content_import_meta.json"
    assert draft_path.exists()
    assert meta_path.exists()
    assert not (output_dir / "spec_content_applied.json").exists()
