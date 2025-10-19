from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import app


SAMPLE_SPEC = Path("samples/json/sample_spec.json")
SAMPLE_CONTENT = Path("samples/json/sample_content_approved.json")
SAMPLE_REVIEW = Path("samples/json/sample_content_review_log.json")


def test_draft_generates_outputs(tmp_path) -> None:
    output_dir = tmp_path / "draft"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "outline",
            str(SAMPLE_SPEC),
            "--content-approved",
            str(SAMPLE_CONTENT),
            "--content-review-log",
            str(SAMPLE_REVIEW),
            "--output",
            str(output_dir),
            "--appendix-limit",
            "3",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    draft_path = output_dir / "draft_draft.json"
    approved_path = output_dir / "draft_approved.json"
    log_path = output_dir / "draft_review_log.json"
    meta_path = output_dir / "draft_meta.json"

    for path in (draft_path, approved_path, log_path, meta_path):
        assert path.exists()

    draft_payload = json.loads(approved_path.read_text(encoding="utf-8"))
    assert len(draft_payload.get("sections", [])) >= 1

    meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta_payload["slides"] >= 1
    assert meta_payload["appendix_limit"] == 3
    assert Path(meta_payload["paths"]["draft_approved"]).name == "draft_approved.json"
