"""Draft structuring pipeline step tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptx_generator.models import ContentApprovalDocument
from pptx_generator.pipeline import DraftStructuringOptions, DraftStructuringStep
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.models import JobSpec


@pytest.fixture()
def sample_spec() -> JobSpec:
    spec_path = Path("samples/json/sample_spec.json")
    return JobSpec.parse_file(spec_path)


@pytest.fixture()
def content_approved() -> ContentApprovalDocument:
    payload = Path("samples/json/sample_content_approved.json").read_text(encoding="utf-8")
    return ContentApprovalDocument.model_validate_json(payload)


def test_draft_structuring_generates_documents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_spec: JobSpec, content_approved: ContentApprovalDocument) -> None:
    monkeypatch.setenv("DRAFT_STORE_DIR", str(tmp_path / "store"))

    layouts_path = tmp_path / "layouts.jsonl"
    layouts_path.write_text(
        '\n'.join(
            [
                json.dumps(
                    {
                        "layout_id": "Title",
                        "usage_tags": ["title"],
                        "text_hint": {"max_lines": 3},
                        "media_hint": {"allow_table": False},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "layout_id": "Content",
                        "usage_tags": ["content", "problem"],
                        "text_hint": {"max_lines": 6},
                        "media_hint": {"allow_table": True},
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    context = PipelineContext(spec=sample_spec, workdir=tmp_path)
    context.add_artifact("content_approved", content_approved)

    step = DraftStructuringStep(
        DraftStructuringOptions(
            layouts_path=layouts_path,
            output_dir=tmp_path,
        )
    )
    step.run(context)

    draft_path = tmp_path / "draft_approved.json"
    assert draft_path.exists()

    payload = json.loads(draft_path.read_text(encoding="utf-8"))
    assert payload["sections"], "sections should not be empty"
    first_section = payload["sections"][0]
    assert first_section["slides"], "slides should not be empty"
    first_slide = first_section["slides"][0]
    assert first_slide["layout_hint"], "layout_hint should be populated"
    assert first_slide["layout_candidates"], "layout_candidates should not be empty"

    assert context.artifacts["draft_document_path"] == str(draft_path)
    assert (tmp_path / "draft_review_log.json").exists()
