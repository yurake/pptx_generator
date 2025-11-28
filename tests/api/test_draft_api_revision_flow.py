"""Draft API behavior tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pptx_generator.api.draft_app import create_draft_app
from pptx_generator.api.draft_store import DraftStore
from pptx_generator.models import (DraftDocument, DraftLayoutCandidate,
                                   DraftMeta, DraftSection, DraftSlideCard)


def _locked_board() -> DraftDocument:
    return DraftDocument(
        sections=[
            DraftSection(
                name="Section",
                order=1,
                status="approved",
                slides=[
                    DraftSlideCard(
                        ref_id="slide-1",
                        order=1,
                        layout_hint="Title",
                        locked=True,
                        status="approved",
                        layout_candidates=[DraftLayoutCandidate(layout_id="Title", score=1.0)],
                    )
                ],
            )
        ],
        meta=DraftMeta(target_length=1, structure_pattern="default", appendix_limit=3),
    )


def test_locked_slide_returns_423(tmp_path) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-locked", _locked_board())
    app = create_draft_app(store)
    client = TestClient(app)

    response = client.patch(
        "/v1/draft/slides/slide-1/hint",
        params={"spec_id": "spec-locked"},
        headers={"If-Match": etag},
        json={"layout_hint": "New", "notes": "attempt"},
    )

    assert response.status_code == 423
    assert "ロック" in response.json()["detail"]
