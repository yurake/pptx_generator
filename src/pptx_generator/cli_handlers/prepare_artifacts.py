from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from pptx_generator.prepare import PrepareCard, PrepareDocument
from pptx_generator.prepare.models import PrepareGenerationMeta

from .prepare_models import PrepareCommandResult, PrepareStaticContext


class PrepareCommandArtifacts:
    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.cards_path = output_dir / "prepare_card.json"
        self.log_path = output_dir / "prepare_log.json"
        self.ai_log_path = output_dir / "prepare_ai_log.json"
        self.meta_path = output_dir / "ai_generation_meta.json"
        self.story_outline_path = output_dir / "prepare_story_outline.json"
        self.audit_path = output_dir / "audit_log.json"

    @classmethod
    def initialize(cls, output_dir: Path) -> "PrepareCommandArtifacts":
        output_dir.mkdir(parents=True, exist_ok=True)
        return cls(output_dir=output_dir)

    def write_outputs(
        self,
        *,
        document: PrepareDocument,
        meta: PrepareGenerationMeta,
        ai_logs: Sequence[Any],
        dump_json: Callable[[Path, object], None],
        static_context: PrepareStaticContext,
        messages: list[str],
        import_metadata: list[dict[str, Any]] | None = None,
    ) -> PrepareCommandResult:
        document.meta = dict(document.meta or {})
        document.meta.update(
            {
                "prepare_card_path": _relativize(self.cards_path, self.output_dir),
                "prepare_log_path": _relativize(self.log_path, self.output_dir),
                "prepare_ai_log_path": _relativize(self.ai_log_path, self.output_dir),
                "ai_generation_meta_path": _relativize(self.meta_path, self.output_dir),
                "prepare_story_outline_path": _relativize(self.story_outline_path, self.output_dir),
                "prepare_audit_log_path": _relativize(self.audit_path, self.output_dir),
            }
        )

        dump_json(self.cards_path, document.model_dump(mode="json", exclude_none=True))
        dump_json(self.log_path, [])
        dump_json(
            self.ai_log_path,
            [record.model_dump(mode="json", exclude_none=True) for record in ai_logs],
        )
        dump_json(self.meta_path, meta.model_dump(mode="json", exclude_none=True))
        dump_json(self.story_outline_path, _build_prepare_story_outline(document))

        audit_payload: dict[str, Any] = {
            "prepare_normalization": {
                "generated_at": meta.generated_at.isoformat(),
                "policy_id": meta.policy_id,
                "input_hash": meta.input_hash,
                "mode": meta.mode,
                "outputs": {
                    "prepare_card": str(self.cards_path.resolve()),
                    "prepare_log": str(self.log_path.resolve()),
                    "prepare_ai_log": str(self.ai_log_path.resolve()),
                    "ai_generation_meta": str(self.meta_path.resolve()),
                    "prepare_story_outline": str(self.story_outline_path.resolve()),
                },
                "statistics": meta.statistics,
            }
        }
        if static_context.template_spec_path is not None:
            audit_payload["prepare_normalization"]["outputs"]["template_spec"] = str(
                static_context.template_spec_path
            )
        if static_context.blueprint_ref is not None:
            audit_payload["prepare_normalization"]["blueprint"] = static_context.blueprint_ref
        if meta.slot_coverage:
            audit_payload["prepare_normalization"]["slot_summary"] = meta.slot_coverage
        if import_metadata:
            audit_payload["prepare_normalization"]["import_sources"] = import_metadata
        dump_json(self.audit_path, audit_payload)

        return PrepareCommandResult(
            cards_path=self.cards_path,
            log_path=self.log_path,
            ai_log_path=self.ai_log_path,
            meta_path=self.meta_path,
            story_outline_path=self.story_outline_path,
            audit_path=self.audit_path,
            messages=messages,
        )


def _relativize(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _build_prepare_story_outline(document: PrepareDocument) -> dict[str, Any]:
    chapter_cards: dict[str, list[str]] = {}

    def resolve_bucket(card: PrepareCard) -> str:
        if isinstance(card.meta, dict):
            source_chapter = card.meta.get("source_chapter")
            if isinstance(source_chapter, dict):
                source_id = source_chapter.get("id")
                source_title = source_chapter.get("title")
                if isinstance(source_id, str) and source_id.strip():
                    return source_id.strip()
                if isinstance(source_title, str) and source_title.strip():
                    return source_title.strip()
        blueprint = card.blueprint_meta()
        if blueprint and blueprint.get("slide_id"):
            return str(blueprint.get("slide_id"))
        return card.role.story_phase or card.card_id or "unlabeled"

    for card in document.cards:
        bucket = resolve_bucket(card)
        chapter_cards.setdefault(bucket, []).append(card.card_id)

    chapters_payload: list[dict[str, Any]] = []
    for chapter in document.story_context.chapters:
        cards = chapter_cards.pop(chapter.id, [])
        if not cards:
            cards = chapter_cards.pop(chapter.title, [])
        chapters_payload.append(
            {
                "id": chapter.id,
                "title": chapter.title,
                "cards": cards,
            }
        )

    for title, cards in chapter_cards.items():
        chapters_payload.append({"id": title, "title": title, "cards": cards})

    return {
        "prepare_id": document.prepare_id,
        "chapters": chapters_payload,
        "narrative_theme": None,
        "summary": None,
    }


__all__ = [
    "PrepareCommandArtifacts",
]
