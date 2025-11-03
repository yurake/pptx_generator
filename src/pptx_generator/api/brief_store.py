"""ファイルベースのブリーフ承認ストア。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ..brief import BriefCard, BriefSupportingPoint, BriefStoryInfo


class SpecNotFoundError(KeyError):
    """指定した spec_id が存在しない。"""


class CardNotFoundError(KeyError):
    """指定した card_id が存在しない。"""


class RevisionMismatchError(RuntimeError):
    """ETag が一致しない場合に発生する。"""


class SpecAlreadyExistsError(RuntimeError):
    """既に存在する spec を作成しようとした。"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _etag_from_revision(revision: int) -> str:
    return f'W/"brief-{revision}"'


def _parse_etag(etag: str) -> int:
    if not etag:
        raise RevisionMismatchError("ETag が指定されていません")
    prefix = 'W/"brief-'
    if not etag.startswith(prefix) or not etag.endswith('"'):
        raise RevisionMismatchError(f"ETag の形式が正しくありません: {etag}")
    value = etag[len(prefix) : -1]
    try:
        return int(value)
    except ValueError as exc:
        raise RevisionMismatchError(f"ETag の値が整数ではありません: {etag}") from exc


def _hash_json(text: str) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


@dataclass(slots=True)
class BriefCardState:
    card: BriefCard

    def to_dict(self) -> dict[str, Any]:
        return {"card": self.card.model_dump(mode="json")}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BriefCardState":
        card = BriefCard.model_validate(payload["card"])
        return cls(card=card)


class BriefStore:
    """シンプルなファイルベースのストア。"""

    def __init__(self, base_dir: Path | None = None) -> None:
        env_dir = os.environ.get("BRIEF_STORE_DIR")
        self._base_dir = base_dir or Path(env_dir or ".brief/store")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 公開 API
    # ------------------------------------------------------------------ #
    def create_cards(self, spec_id: str, cards: list[BriefCardState]) -> str:
        state_path = self._spec_path(spec_id)
        if state_path.exists():
            raise SpecAlreadyExistsError(f"spec '{spec_id}' は既に存在します")
        state = {
            "spec_id": spec_id,
            "revision": 1,
            "cards": {card.card.card_id: card.to_dict() for card in cards},
            "logs": [],
        }
        self._write_state(spec_id, state)
        return _etag_from_revision(state["revision"])

    def update_card(
        self,
        spec_id: str,
        card_id: str,
        *,
        chapter: str | None,
        message: str | None,
        narrative: list[str] | None,
        supporting_points: list[dict[str, Any]] | None,
        story: dict[str, Any] | None,
        intent_tags: list[str] | None,
        autofix_applied: list[str] | None,
        expected_etag: str,
        actor: str | None,
    ) -> tuple[str, str]:
        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        card_state = self._get_card_state(state, card_id)
        card = card_state.card

        if chapter is not None:
            card.chapter = chapter
        if message is not None:
            card.message = message
        if narrative is not None:
            card.narrative = list(narrative)
        if supporting_points is not None:
            card.supporting_points = [
                BriefSupportingPoint(
                    statement=item["statement"],
                    evidence=(
                        None
                        if not item.get("evidence_type")
                        else {"type": item["evidence_type"], "value": item.get("evidence_value")}
                    ),
                )
                for item in supporting_points
            ]
        if story is not None:
            card.story = BriefStoryInfo.model_validate(story)
        if intent_tags is not None:
            card.intent_tags = [tag for tag in intent_tags if tag]
        if autofix_applied:
            existing = set(card.autofix_applied)
            for patch_id in autofix_applied:
                if patch_id not in existing:
                    card.autofix_applied.append(patch_id)
                    existing.add(patch_id)

        state["cards"][card_id] = card_state.to_dict()
        state["revision"] += 1
        self._append_log(
            state,
            {
                "spec_id": spec_id,
                "card_id": card_id,
                "action": "update",
                "actor": actor,
                "timestamp": _now_iso(),
                "notes": None,
                "applied_autofix": autofix_applied,
            },
        )
        self._write_state(spec_id, state)
        content_hash_raw = json.dumps(card.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return _etag_from_revision(state["revision"]), _hash_json(content_hash_raw)

    def approve_card(
        self,
        spec_id: str,
        card_id: str,
        *,
        notes: str | None,
        applied_autofix: list[str] | None,
        expected_etag: str,
        actor: str | None,
    ) -> tuple[str, str, datetime]:
        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        card_state = self._get_card_state(state, card_id)
        if card_state.card.status != "approved":
            card_state.card.status = "approved"
        if applied_autofix:
            existing = set(card_state.card.autofix_applied)
            for patch_id in applied_autofix:
                if patch_id not in existing:
                    card_state.card.autofix_applied.append(patch_id)
                    existing.add(patch_id)

        locked_at = datetime.now(timezone.utc)

        state["cards"][card_id] = card_state.to_dict()
        state["revision"] += 1
        self._append_log(
            state,
            {
                "spec_id": spec_id,
                "card_id": card_id,
                "action": "approve",
                "actor": actor,
                "timestamp": locked_at.isoformat(),
                "notes": notes,
                "applied_autofix": applied_autofix,
            },
        )
        self._write_state(spec_id, state)
        return _etag_from_revision(state["revision"]), card_state.card.status, locked_at

    def return_card(
        self,
        spec_id: str,
        card_id: str,
        *,
        reason: str,
        requested_by: str | None,
        expected_etag: str,
        actor: str | None,
    ) -> tuple[str, str]:
        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        card_state = self._get_card_state(state, card_id)
        card_state.card.status = "returned"

        state["cards"][card_id] = card_state.to_dict()
        state["revision"] += 1
        self._append_log(
            state,
            {
                "spec_id": spec_id,
                "card_id": card_id,
                "action": "return",
                "actor": actor or requested_by,
                "timestamp": _now_iso(),
                "notes": reason,
                "applied_autofix": None,
            },
        )
        self._write_state(spec_id, state)
        return _etag_from_revision(state["revision"]), card_state.card.status

    def get_card(self, spec_id: str, card_id: str) -> tuple[BriefCardState, str]:
        state = self._load_state(spec_id)
        card_state = self._get_card_state(state, card_id)
        etag = _etag_from_revision(state["revision"])
        return card_state, etag

    def list_logs(
        self,
        *,
        spec_id: str | None,
        action: str | None,
        since: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int | None]:
        logs: list[dict[str, Any]] = []
        for candidate_spec_id in self._iter_spec_ids():
            if spec_id and candidate_spec_id != spec_id:
                continue
            state = self._load_state(candidate_spec_id)
            for entry in state["logs"]:
                if action and entry["action"] != action:
                    continue
                if since and datetime.fromisoformat(entry["timestamp"]) < since:
                    continue
                logs.append(entry)

        logs.sort(key=lambda item: item["timestamp"])
        sliced = logs[offset : offset + limit]
        next_offset = offset + len(sliced)
        if next_offset >= len(logs):
            next_offset = None
        return sliced, next_offset

    # ------------------------------------------------------------------ #
    # 内部ユーティリティ
    # ------------------------------------------------------------------ #
    def _spec_path(self, spec_id: str) -> Path:
        return self._base_dir / f"{spec_id}.json"

    def _write_state(self, spec_id: str, state: dict[str, Any]) -> None:
        path = self._spec_path(spec_id)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_state(self, spec_id: str) -> dict[str, Any]:
        path = self._spec_path(spec_id)
        if not path.exists():
            raise SpecNotFoundError(spec_id)
        text = path.read_text(encoding="utf-8")
        return json.loads(text)

    def _get_card_state(self, state: dict[str, Any], card_id: str) -> BriefCardState:
        cards = state.get("cards") or {}
        payload = cards.get(card_id)
        if payload is None:
            raise CardNotFoundError(card_id)
        return BriefCardState.from_dict(payload)

    def _ensure_revision(self, state: dict[str, Any], expected: int) -> None:
        revision = int(state.get("revision", 0))
        if revision != expected:
            raise RevisionMismatchError(f"ETag が一致しません: expected={expected}, actual={revision}")

    def _append_log(self, state: dict[str, Any], entry: dict[str, Any]) -> None:
        logs: list[dict[str, Any]] = state.setdefault("logs", [])
        logs.append(entry)

    def _iter_spec_ids(self) -> Iterator[str]:
        for path in self._base_dir.glob("*.json"):
            yield path.stem
