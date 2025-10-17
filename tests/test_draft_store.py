"""DraftStore unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.api.draft_store import (DraftStore, RevisionMismatchError,
                                            SlideLockedError)
from pptx_generator.models import (DraftDocument, DraftLayoutCandidate,
                                   DraftMeta, DraftSection, DraftSlideCard)


@pytest.fixture()
def draft_board() -> DraftDocument:
    return DraftDocument(
        sections=[
            DraftSection(
                name="Section A",
                order=1,
                slides=[
                    DraftSlideCard(
                        ref_id="s1",
                        order=1,
                        layout_hint="Title",
                        layout_candidates=[DraftLayoutCandidate(layout_id="Title", score=0.9)],
                    ),
                    DraftSlideCard(
                        ref_id="s2",
                        order=2,
                        layout_hint="Agenda",
                        layout_candidates=[DraftLayoutCandidate(layout_id="Agenda", score=0.8)],
                    ),
                ],
            ),
            DraftSection(
                name="Section B",
                order=2,
                slides=[
                    DraftSlideCard(
                        ref_id="s3",
                        order=1,
                        layout_hint="Content",
                        layout_candidates=[DraftLayoutCandidate(layout_id="Content", score=0.7)],
                    ),
                ],
            ),
        ],
        meta=DraftMeta(target_length=3, structure_pattern="default", appendix_limit=5),
    )


def test_draft_store_operations(tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-1", draft_board)

    new_etag = store.update_layout_hint(
        spec_id="spec-1",
        slide_id="s1",
        layout_hint="TitleAlt",
        notes="adjusted layout",
        expected_etag=etag,
        actor="tester",
    )
    assert new_etag != etag

    etag = store.move_slide(
        spec_id="spec-1",
        slide_id="s2",
        target_section="Section B",
        position=1,
        expected_etag=new_etag,
        actor="tester",
    )

    etag = store.set_appendix(
        spec_id="spec-1",
        slide_id="s3",
        appendix=True,
        expected_etag=etag,
        actor="tester",
        notes="appendix",
    )

    etag = store.approve_section(
        spec_id="spec-1",
        section_name="Section B",
        expected_etag=etag,
        actor="approver",
        notes="ok",
    )

    board, current_etag = store.get_board("spec-1")
    assert current_etag == etag
    section_b = next(section for section in board.sections if section.name == "Section B")
    assert section_b.slides[0].ref_id == "s2"
    assert section_b.slides[0].order == 1
    assert section_b.slides[0].status == "approved"
    assert section_b.slides[0].locked is True
    assert section_b.slides[1].appendix is True

    logs, next_offset = store.list_logs("spec-1", limit=10, offset=0)
    assert len(logs) == 4
    assert next_offset is None


def test_revision_mismatch(tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-2", draft_board)

    with pytest.raises(RevisionMismatchError):
        store.update_layout_hint(
            spec_id="spec-2",
            slide_id="s1",
            layout_hint="Alt",
            notes=None,
            expected_etag='W/"draft-999"',
            actor=None,
        )


def test_locked_slide_rejects_updates(tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-3", draft_board)

    etag = store.approve_section(
        spec_id="spec-3",
        section_name="Section A",
        expected_etag=etag,
        actor="approver",
        notes="ok",
    )

    with pytest.raises(SlideLockedError):
        store.update_layout_hint(
            spec_id="spec-3",
            slide_id="s1",
            layout_hint="Locked",  # 変更されない想定
            notes=None,
            expected_etag=etag,
            actor="editor",
        )

    with pytest.raises(SlideLockedError):
        store.move_slide(
            spec_id="spec-3",
            slide_id="s1",
            target_section="Section B",
            position=1,
            expected_etag=etag,
            actor="editor",
        )

    with pytest.raises(SlideLockedError):
        store.set_appendix(
            spec_id="spec-3",
            slide_id="s1",
            appendix=True,
            expected_etag=etag,
            actor="editor",
            notes=None,
        )

    board, current_etag = store.get_board("spec-3")
    assert current_etag == etag
    section_a = next(section for section in board.sections if section.name == "Section A")
    target_slide = next(slide for slide in section_a.slides if slide.ref_id == "s1")
    assert target_slide.layout_hint == "Title"
    assert target_slide.appendix is False

    logs, next_offset = store.list_logs("spec-3", limit=10, offset=0)
    assert len(logs) == 1
    assert next_offset is None
