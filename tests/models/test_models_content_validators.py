from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pptx_generator.models import (
    AutoFixProposal,
    ContentApprovalDocument,
    ContentElements,
    ContentReviewLogEntry,
    ContentSlide,
    ContentSlideSource,
    ContentTableData,
    JsonPatchOperation,
)


def test_content_table_data_normalizes_rows_and_headers() -> None:
    data = ContentTableData(headers=["title", "value"], rows=[[1, 2], ["foo", 3.5]])

    assert data.rows == [["1", "2"], ["foo", "3.5"]]


def test_content_table_data_validates_row_length() -> None:
    with pytest.raises(ValueError):
        ContentTableData(headers=["title", "value"], rows=[[1]])


def test_content_elements_normalize_body_variants() -> None:
    none_body = ContentElements(title="Sample", body=None)  # type: ignore[arg-type]
    assert none_body.body == []

    list_body = ContentElements(title="Another", body=["foo", "bar"])
    assert list_body.body == ["foo", "bar"]

    scalar_body = ContentElements(title="Scalar", body="single line")  # type: ignore[arg-type]
    assert scalar_body.body == ["single line"]


def test_content_elements_normalize_subtitle() -> None:
    assert ContentElements(title="No subtitle", subtitle=None).subtitle is None
    assert ContentElements(title="Trim", subtitle="  ").subtitle is None
    assert ContentElements(title="Value", subtitle=" Text ").subtitle == "Text"


def test_json_patch_operation_validators() -> None:
    op = JsonPatchOperation(op="add", path="/sample", value=1)
    assert op.path == "/sample"

    with pytest.raises(ValueError):
        JsonPatchOperation(op="add", path="invalid", value=1)

    with pytest.raises(ValueError):
        JsonPatchOperation(op="move", path="/target", from_path="source")  # type: ignore[arg-type]


def test_autofix_proposal_normalization_and_validation() -> None:
    with pytest.raises(ValueError):
        AutoFixProposal(patch_id="a", description="desc", patch=None)  # type: ignore[arg-type]

    single = AutoFixProposal(
        patch_id="b",
        description="desc",
        patch=JsonPatchOperation(op="add", path="/foo", value="bar"),
    )
    assert len(single.patch) == 1

    with pytest.raises(ValueError):
        AutoFixProposal(patch_id="c", description="desc", patch=[])  # type: ignore[arg-type]


def test_content_slide_source_normalizes_intent_tags() -> None:
    none_tags = ContentSlideSource(intent_tags=None)  # type: ignore[arg-type]
    assert none_tags.intent_tags == ()

    list_tags = ContentSlideSource(intent_tags=[" Foo ", "foo", "Bar"])
    assert list_tags.intent_tags == ("Foo", "Bar")

    string_tag = ContentSlideSource(intent_tags=" solo ")  # type: ignore[arg-type]
    assert string_tag.intent_tags == ("solo",)


def test_content_slide_and_document_helpers() -> None:
    elements = ContentElements(title="Slide", body=["one"])
    slide = ContentSlide(id="1", intent="demo", elements=elements, applied_autofix=None)  # type: ignore[arg-type]
    assert slide.applied_autofix == []

    slide_with_autofix = ContentSlide(id="2", intent="demo", elements=elements, applied_autofix=["fix"])
    assert slide_with_autofix.applied_autofix == ["fix"]

    doc = ContentApprovalDocument(slides=[slide_with_autofix.model_copy(update={"status": "approved"})])
    doc.ensure_all_approved()

    doc_with_pending = ContentApprovalDocument(slides=[slide])
    with pytest.raises(ValueError):
        doc_with_pending.ensure_all_approved()


def test_content_review_log_entry_normalizes_autofix() -> None:
    entry = ContentReviewLogEntry(
        slide_id="1",
        action="approve",
        actor="tester",
        timestamp=datetime.now(timezone.utc),
        applied_autofix=None,  # type: ignore[arg-type]
    )
    assert entry.applied_autofix == []

    entry_with_list = ContentReviewLogEntry(
        slide_id="1",
        action="approve",
        actor="tester",
        timestamp=datetime.now(timezone.utc),
        applied_autofix=["fix"],
    )
    assert entry_with_list.applied_autofix == ["fix"]
