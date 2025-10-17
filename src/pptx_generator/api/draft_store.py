"""ドラフト構成管理用のシンプルなストア。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Tuple

from ..models import DraftDocument, DraftLogEntry


class BoardNotFoundError(KeyError):
    """指定した spec_id が存在しない。"""


class SlideNotFoundError(KeyError):
    """指定したスライドが存在しない。"""


class SectionNotFoundError(KeyError):
    """指定したセクションが存在しない。"""


class RevisionMismatchError(RuntimeError):
    """ETag が一致しない場合に発生する。"""


class BoardAlreadyExistsError(RuntimeError):
    """既に存在するボードを作成しようとした。"""


def _etag_from_revision(revision: int) -> str:
    return f'W/"draft-{revision}"'


def _parse_etag(etag: str) -> int:
    if not etag:
        raise RevisionMismatchError("ETag が指定されていません")
    prefix = 'W/"draft-'
    if not etag.startswith(prefix) or not etag.endswith('"'):
        raise RevisionMismatchError(f"ETag の形式が正しくありません: {etag}")
    value = etag[len(prefix) : -1]
    try:
        return int(value)
    except ValueError as exc:
        msg = f"ETag の値が整数ではありません: {etag}"
        raise RevisionMismatchError(msg) from exc


@dataclass(slots=True)
class DraftState:
    """ファイルに保存するドラフト構成の状態。"""

    spec_id: str
    revision: int
    board: dict[str, Any]
    logs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "revision": self.revision,
            "board": self.board,
            "logs": self.logs,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DraftState":
        return cls(
            spec_id=payload["spec_id"],
            revision=payload["revision"],
            board=payload["board"],
            logs=payload.get("logs", []),
        )


class DraftStore:
    """ドラフト構成用のストア。"""

    def __init__(self, base_dir: Path | None = None) -> None:
        env_dir = os.environ.get("DRAFT_STORE_DIR")
        self._base_dir = base_dir or Path(env_dir or ".pptx/draft_store")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 公開 API
    # ------------------------------------------------------------------ #
    def create_board(self, spec_id: str, board: DraftDocument) -> str:
        state_path = self._spec_path(spec_id)
        if state_path.exists():
            raise BoardAlreadyExistsError(f"spec '{spec_id}' は既に存在します")

        state = DraftState(
            spec_id=spec_id,
            revision=1,
            board=board.model_dump(mode="json"),
            logs=[],
        )
        self._write_state(state)
        return _etag_from_revision(state.revision)

    def overwrite_board(self, spec_id: str, board: DraftDocument) -> str:
        state = DraftState(
            spec_id=spec_id,
            revision=1,
            board=board.model_dump(mode="json"),
            logs=[],
        )
        self._write_state(state)
        return _etag_from_revision(state.revision)

    def get_board(self, spec_id: str) -> Tuple[DraftDocument, str]:
        state = self._load_state(spec_id)
        board = DraftDocument.model_validate(state.board)
        return board, _etag_from_revision(state.revision)

    def update_layout_hint(
        self,
        spec_id: str,
        slide_id: str,
        *,
        layout_hint: str,
        notes: str | None,
        expected_etag: str,
        actor: str | None,
    ) -> str:
        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        section, slide = self._find_slide(state.board, slide_id)
        slide["layout_hint"] = layout_hint

        candidates = slide.setdefault("layout_candidates", [])
        if not any(candidate.get("layout_id") == layout_hint for candidate in candidates):
            candidates.append({"layout_id": layout_hint, "score": 1.0})

        state.revision += 1
        self._append_log(
            state,
            DraftLogEntry(
                target_type="slide",
                target_id=slide_id,
                action="hint",
                actor=actor,
                timestamp=datetime.now(timezone.utc),
                notes=notes,
                changes={"layout_hint": layout_hint},
            ).model_dump(mode="json"),
        )
        self._write_state(state)
        return _etag_from_revision(state.revision)

    def move_slide(
        self,
        spec_id: str,
        slide_id: str,
        *,
        target_section: str,
        position: int | None,
        expected_etag: str,
        actor: str | None,
    ) -> str:
        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        source_section, slide = self._find_slide(state.board, slide_id)
        source_section["slides"] = [item for item in source_section["slides"] if item["ref_id"] != slide_id]

        destination = self._find_section(state.board, target_section)
        insert_at = len(destination["slides"]) if position is None else max(0, min(position - 1, len(destination["slides"])))
        destination["slides"].insert(insert_at, slide)

        self._reorder_slides(source_section["slides"])
        if destination is not source_section:
            self._reorder_slides(destination["slides"])

        state.revision += 1
        self._append_log(
            state,
            DraftLogEntry(
                target_type="slide",
                target_id=slide_id,
                action="move",
                actor=actor,
                timestamp=datetime.now(timezone.utc),
                notes=None,
                changes={
                    "from_section": source_section["name"],
                    "to_section": destination["name"],
                    "position": insert_at + 1,
                },
            ).model_dump(mode="json"),
        )
        self._write_state(state)
        return _etag_from_revision(state.revision)

    def approve_section(
        self,
        spec_id: str,
        section_name: str,
        *,
        expected_etag: str,
        actor: str | None,
        notes: str | None,
    ) -> str:
        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        section = self._find_section(state.board, section_name)
        section["status"] = "approved"
        for slide in section.get("slides", []):
            slide["status"] = "approved"
            slide["locked"] = True

        state.revision += 1
        self._append_log(
            state,
            DraftLogEntry(
                target_type="section",
                target_id=section_name,
                action="approve",
                actor=actor,
                timestamp=datetime.now(timezone.utc),
                notes=notes,
                changes=None,
            ).model_dump(mode="json"),
        )
        self._write_state(state)
        return _etag_from_revision(state.revision)

    def set_appendix(
        self,
        spec_id: str,
        slide_id: str,
        *,
        appendix: bool,
        expected_etag: str,
        actor: str | None,
        notes: str | None,
    ) -> str:
        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        _, slide = self._find_slide(state.board, slide_id)
        slide["appendix"] = appendix

        state.revision += 1
        self._append_log(
            state,
            DraftLogEntry(
                target_type="slide",
                target_id=slide_id,
                action="appendix",
                actor=actor,
                timestamp=datetime.now(timezone.utc),
                notes=notes,
                changes={"appendix": appendix},
            ).model_dump(mode="json"),
        )
        self._write_state(state)
        return _etag_from_revision(state.revision)

    def list_logs(
        self,
        spec_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DraftLogEntry], int | None]:
        state = self._load_state(spec_id)
        entries = [
            DraftLogEntry.model_validate(item) for item in state.logs
        ]
        sliced = entries[offset : offset + limit]
        next_offset = offset + len(sliced)
        if next_offset >= len(entries):
            next_offset = None
        return sliced, next_offset

    # ------------------------------------------------------------------ #
    # 内部処理
    # ------------------------------------------------------------------ #
    def _spec_path(self, spec_id: str) -> Path:
        filename = f"{spec_id}.json"
        return self._base_dir / filename

    def _write_state(self, state: DraftState) -> None:
        path = self._spec_path(state.spec_id)
        path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_state(self, spec_id: str) -> DraftState:
        path = self._spec_path(spec_id)
        if not path.exists():
            raise BoardNotFoundError(f"spec '{spec_id}' は存在しません")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DraftState.from_dict(payload)

    @staticmethod
    def _ensure_revision(state: DraftState, expected_revision: int) -> None:
        if state.revision != expected_revision:
            raise RevisionMismatchError(f"ETag が一致しません: expected={expected_revision}, actual={state.revision}")

    @staticmethod
    def _find_section(board: dict[str, Any], section_name: str) -> dict[str, Any]:
        for section in board.get("sections", []):
            if section.get("name") == section_name:
                return section
        raise SectionNotFoundError(f"section '{section_name}' が見つかりません")

    def _find_slide(self, board: dict[str, Any], slide_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for section in board.get("sections", []):
            for slide in section.get("slides", []):
                if slide.get("ref_id") == slide_id:
                    return section, slide
        raise SlideNotFoundError(f"slide '{slide_id}' が見つかりません")

    @staticmethod
    def _reorder_slides(slides: list[dict[str, Any]]) -> None:
        for index, slide in enumerate(slides, start=1):
            slide["order"] = index

    @staticmethod
    def _append_log(state: DraftState, entry: dict[str, Any]) -> None:
        state.logs.append(entry)
