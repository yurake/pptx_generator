"""ファイルベースのコンテンツ承認ストア。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ..models import ContentElements, ContentSlide, ContentTableData


class SpecNotFoundError(KeyError):
    """指定した spec_id が存在しない。"""


class SlideNotFoundError(KeyError):
    """指定した slide_id が存在しない。"""


class RevisionMismatchError(RuntimeError):
    """ETag が一致しない場合に発生する。"""


class SpecAlreadyExistsError(RuntimeError):
    """既に存在する spec を作成しようとした。"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _etag_from_revision(revision: int) -> str:
    return f'W/"cards-{revision}"'


def _parse_etag(etag: str) -> int:
    if not etag:
        msg = "ETag が指定されていません"
        raise RevisionMismatchError(msg)
    prefix = 'W/"cards-'
    if not etag.startswith(prefix) or not etag.endswith('"'):
        msg = f"ETag の形式が正しくありません: {etag}"
        raise RevisionMismatchError(msg)
    value = etag[len(prefix) : -1]
    try:
        return int(value)
    except ValueError as exc:
        msg = f"ETag の値が整数ではありません: {etag}"
        raise RevisionMismatchError(msg) from exc


@dataclass(slots=True)
class CardState:
    """カード状態。"""

    slide: ContentSlide
    story: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "slide": self.slide.model_dump(mode="json"),
        }
        if self.story is not None:
            data["story"] = self.story
        return data

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CardState":
        slide = ContentSlide.model_validate(payload["slide"])
        story = payload.get("story")
        return cls(slide=slide, story=story)


class ContentStore:
    """シンプルなファイルベースのストア。"""

    def __init__(self, base_dir: Path | None = None) -> None:
        env_dir = os.environ.get("CONTENT_STORE_DIR")
        self._base_dir = base_dir or Path(env_dir or ".pptx/content_store")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 公開 API
    # ------------------------------------------------------------------ #
    def create_cards(self, spec_id: str, cards: list[CardState]) -> str:
        """新しい spec を登録する。"""

        state_path = self._spec_path(spec_id)
        if state_path.exists():
            msg = f"spec '{spec_id}' は既に存在します"
            raise SpecAlreadyExistsError(msg)
        state = {
            "spec_id": spec_id,
            "revision": 1,
            "cards": {card.slide.id: card.to_dict() for card in cards},
            "logs": [],
        }
        self._write_state(spec_id, state)
        return _etag_from_revision(state["revision"])

    def update_card(
        self,
        spec_id: str,
        slide_id: str,
        *,
        title: str | None,
        body: list[str] | None,
        table_data: ContentTableData | None,
        note: str | None,
        intent: str | None,
        type_hint: str | None,
        story: dict[str, Any] | None,
        autofix_applied: list[str] | None,
        expected_etag: str,
        actor: str | None,
    ) -> tuple[str, str]:
        """カード内容を更新する。"""

        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        card_state = self._get_card_state(state, slide_id)
        slide = card_state.slide

        if slide.status == "approved":
            msg = f"slide '{slide_id}' は既に承認済みのため更新できません"
            raise RevisionMismatchError(msg)

        elements = slide.elements
        if title is not None:
            elements.title = title
        if body is not None:
            elements.body = body
        if table_data is not None:
            elements.table_data = table_data
        if note is not None:
            elements.note = note
        if intent is not None:
            slide.intent = intent
        if type_hint is not None:
            slide.type_hint = type_hint
        if story is not None:
            card_state.story = story
        if autofix_applied:
            existing = set(slide.applied_autofix)
            for patch_id in autofix_applied:
                if patch_id not in existing:
                    slide.applied_autofix.append(patch_id)
                    existing.add(patch_id)

        content_payload = slide.elements.model_dump(mode="json")
        content_hash_raw = json.dumps(content_payload, ensure_ascii=False, sort_keys=True)
        state["cards"][slide_id] = card_state.to_dict()
        state["revision"] += 1
        self._append_log(
            state,
            {
                "spec_id": spec_id,
                "slide_id": slide_id,
                "action": "update",
                "actor": actor,
                "timestamp": _now_iso(),
                "notes": None,
                "applied_autofix": autofix_applied,
            },
        )
        self._write_state(spec_id, state)
        return _etag_from_revision(state["revision"]), _hash_json(content_hash_raw)

    def approve_card(
        self,
        spec_id: str,
        slide_id: str,
        *,
        notes: str | None,
        applied_autofix: list[str] | None,
        expected_etag: str,
        actor: str | None,
    ) -> tuple[str, str, datetime]:
        """カードを承認状態へ遷移させる。"""

        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        card_state = self._get_card_state(state, slide_id)
        slide = card_state.slide

        if slide.status != "approved":
            slide.status = "approved"
            locked_at = datetime.now(timezone.utc)
        else:
            locked_at = datetime.now(timezone.utc)

        if applied_autofix:
            existing = set(slide.applied_autofix)
            for patch_id in applied_autofix:
                if patch_id not in existing:
                    slide.applied_autofix.append(patch_id)
                    existing.add(patch_id)

        state["cards"][slide_id] = card_state.to_dict()
        state["revision"] += 1
        self._append_log(
            state,
            {
                "spec_id": spec_id,
                "slide_id": slide_id,
                "action": "approve",
                "actor": actor,
                "timestamp": locked_at.isoformat(),
                "notes": notes,
                "applied_autofix": applied_autofix,
            },
        )
        self._write_state(spec_id, state)
        return _etag_from_revision(state["revision"]), slide.status, locked_at

    def return_card(
        self,
        spec_id: str,
        slide_id: str,
        *,
        reason: str,
        requested_by: str | None,
        expected_etag: str,
        actor: str | None,
    ) -> tuple[str, str]:
        """カードを差戻し状態へ遷移させる。"""

        state = self._load_state(spec_id)
        expected_revision = _parse_etag(expected_etag)
        self._ensure_revision(state, expected_revision)

        card_state = self._get_card_state(state, slide_id)
        slide = card_state.slide
        slide.status = "returned"

        state["cards"][slide_id] = card_state.to_dict()
        state["revision"] += 1
        self._append_log(
            state,
            {
                "spec_id": spec_id,
                "slide_id": slide_id,
                "action": "return",
                "actor": actor or requested_by,
                "timestamp": _now_iso(),
                "notes": reason,
                "applied_autofix": None,
            },
        )
        self._write_state(spec_id, state)
        return _etag_from_revision(state["revision"]), slide.status

    def get_card(self, spec_id: str, slide_id: str) -> tuple[CardState, str]:
        """カード情報と現在の ETag を返す。"""

        state = self._load_state(spec_id)
        card_state = self._get_card_state(state, slide_id)
        return card_state, _etag_from_revision(state["revision"])

    def list_logs(
        self,
        *,
        spec_id: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int | None]:
        """監査ログ一覧を返す。"""

        logs = []
        for state in self._iter_states(spec_id):
            for entry in state.get("logs", []):
                if spec_id and entry["spec_id"] != spec_id:
                    continue
                if action and entry["action"] != action:
                    continue
                if since and datetime.fromisoformat(entry["timestamp"]) < since:
                    continue
                logs.append(entry)

        logs.sort(key=lambda item: item["timestamp"])
        sliced = logs[offset : offset + limit]
        next_offset = offset + limit if offset + limit < len(logs) else None
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
            msg = f"spec '{spec_id}' は存在しません"
            raise SpecNotFoundError(msg)
        return json.loads(path.read_text(encoding="utf-8"))

    def _iter_states(self, spec_id: str | None) -> Iterator[dict[str, Any]]:
        if spec_id:
            try:
                yield self._load_state(spec_id)
            except SpecNotFoundError:
                return
            return
        for path in self._base_dir.glob("*.json"):
            try:
                yield json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue

    @staticmethod
    def _get_card_state(state: dict[str, Any], slide_id: str) -> CardState:
        cards = state.get("cards", {})
        raw = cards.get(slide_id)
        if raw is None:
            msg = f"slide '{slide_id}' は存在しません"
            raise SlideNotFoundError(msg)
        return CardState.from_dict(raw)

    @staticmethod
    def _ensure_revision(state: dict[str, Any], expected: int) -> None:
        current = int(state.get("revision", 0))
        if expected != current:
            msg = f"期待したリビジョン {expected} と現在のリビジョン {current} が一致しません"
            raise RevisionMismatchError(msg)

    @staticmethod
    def _append_log(state: dict[str, Any], entry: dict[str, Any]) -> None:
        state.setdefault("logs", []).append(entry)


def _hash_json(value: str) -> str:
    # 遅延 import を避けるためここでローカル import
    import hashlib

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
