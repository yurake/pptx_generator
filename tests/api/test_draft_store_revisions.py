"""DraftStore unit tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from pptx_generator.api.draft_store import (DraftStore, LockedContentError,
                                            RevisionMismatchError)
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

    with pytest.raises(LockedContentError):
        store.update_layout_hint(
            spec_id="spec-1",
            slide_id="s2",
            layout_hint="Locked",
            notes=None,
            expected_etag=etag,
            actor="tester",
        )

    with pytest.raises(LockedContentError):
        store.set_appendix(
            spec_id="spec-1",
            slide_id="s2",
            appendix=False,
            expected_etag=etag,
            actor="tester",
            notes=None,
        )

    with pytest.raises(LockedContentError):
        store.move_slide(
            spec_id="spec-1",
            slide_id="s2",
            target_section="Section A",
            position=1,
            expected_etag=etag,
            actor="tester",
        )


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


def test_concurrent_updates_are_rejected(tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-3", draft_board)

    def update(expected: str) -> str:
        return store.update_layout_hint(
            spec_id="spec-3",
            slide_id="s1",
            layout_hint="Parallel",
            notes=None,
            expected_etag=expected,
            actor="parallel-user",
        )

    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures.append(executor.submit(update, etag))
        futures.append(executor.submit(update, etag))

        results: list[str] = []
        errors: list[RevisionMismatchError] = []
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except RevisionMismatchError as exc:
                errors.append(exc)

    assert len(results) == 1
    assert len(errors) == 1

    board, current_etag = store.get_board("spec-3")
    assert board.sections[0].slides[0].layout_hint == "Parallel"
    assert current_etag == results[0]


def test_concurrent_move_slide_rejected(tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-4", draft_board)

    def move(expected: str) -> str:
        return store.move_slide(
            spec_id="spec-4",
            slide_id="s1",
            target_section="Section B",
            position=1,
            expected_etag=expected,
            actor="parallel-user",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(move, etag), executor.submit(move, etag)]
        results: list[str] = []
        errors: list[RevisionMismatchError] = []
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except RevisionMismatchError as exc:
                errors.append(exc)

    assert len(results) == 1
    assert len(errors) == 1
    board, current_etag = store.get_board("spec-4")
    assert board.sections[1].slides[0].ref_id == "s1"
    assert current_etag == results[0]


def test_concurrent_approve_section_rejected(tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-5", draft_board)

    def approve(expected: str) -> str:
        return store.approve_section(
            spec_id="spec-5",
            section_name="Section A",
            expected_etag=expected,
            actor="approver",
            notes=None,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(approve, etag), executor.submit(approve, etag)]
        results: list[str] = []
        errors: list[RevisionMismatchError] = []
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except RevisionMismatchError as exc:
                errors.append(exc)

    assert len(results) == 1
    assert len(errors) == 1
    board, current_etag = store.get_board("spec-5")
    section_a = next(section for section in board.sections if section.name == "Section A")
    assert all(slide.locked is True for slide in section_a.slides)
    assert current_etag == results[0]


def test_concurrent_set_appendix_rejected(tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-6", draft_board)

    def set_appendix(expected: str) -> str:
        return store.set_appendix(
            spec_id="spec-6",
            slide_id="s1",
            appendix=True,
            expected_etag=expected,
            actor="parallel-user",
            notes=None,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(set_appendix, etag), executor.submit(set_appendix, etag)]
        results: list[str] = []
        errors: list[RevisionMismatchError] = []
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except RevisionMismatchError as exc:
                errors.append(exc)

    assert len(results) == 1
    assert len(errors) == 1
    board, current_etag = store.get_board("spec-6")
    section_a = next(section for section in board.sections if section.name == "Section A")
    assert section_a.slides[0].appendix is True
    assert current_etag == results[0]


def test_concurrent_updates_non_posix_lock(monkeypatch, tmp_path: Path, draft_board: DraftDocument) -> None:
    store = DraftStore(base_dir=tmp_path)
    etag = store.create_board("spec-7", draft_board)

    # 非POSIX想定: fcntl を使わない分岐を通す
    monkeypatch.setattr("pptx_generator.api.draft_store.os.name", "nt")

    def update(expected: str) -> str:
        return store.update_layout_hint(
            spec_id="spec-7",
            slide_id="s1",
            layout_hint="ParallelNonPosix",
            notes=None,
            expected_etag=expected,
            actor="parallel-user",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(update, etag), executor.submit(update, etag)]
        results: list[str] = []
        errors: list[RevisionMismatchError] = []
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except RevisionMismatchError as exc:
                errors.append(exc)

    assert len(results) == 1
    assert len(errors) == 1
    board, current_etag = store.get_board("spec-7")
    assert board.sections[0].slides[0].layout_hint == "ParallelNonPosix"
    assert current_etag == results[0]
