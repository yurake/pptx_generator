"""Tests for the prepare_ai orchestrator helpers."""

from __future__ import annotations

from pptx_generator.models import TemplateBlueprint, TemplateBlueprintSlide, TemplateBlueprintSlot
from pptx_generator.prepare.source import (
    PrepareSourceChapter,
    PrepareSourceDocument,
    PrepareSourceMeta,
    PrepareSourceSupportingPoint,
)
from pptx_generator.prepare_ai.client import MockPrepareLLMClient
from pptx_generator.prepare_ai.orchestrator import PrepareAIOrchestrator, StaticPromptOverride


def _build_source() -> PrepareSourceDocument:
    chapter_a = PrepareSourceChapter(
        id="intro",
        title="Introduction",
        message="Intro message",
        details=["Intro detail"],
        supporting_points=[PrepareSourceSupportingPoint(statement="Intro point")],
        intent_tags=["introduction"],
    )
    chapter_b = PrepareSourceChapter(
        id="detail",
        title="Detail",
        message="Detail message",
        details=["First line", "Second line"],
        supporting_points=[PrepareSourceSupportingPoint(statement="Detail note")],
        intent_tags=["solution"],
    )
    return PrepareSourceDocument(
        meta=PrepareSourceMeta(title="Demo Deck", objective="Grow revenue"),
        chapters=[chapter_a, chapter_b],
        raw_text="## Introduction\n- bullet one\n## Detail\n- bullet two",
    )


def _build_blueprint() -> TemplateBlueprint:
    return TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="slide-1",
                layout="Title",
                required=True,
                intent_tags=["introduction"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="title-slot",
                        anchor="TITLE",
                        content_type="text",
                        required=True,
                        intent_tags=["introduction"],
                    )
                ],
            ),
            TemplateBlueprintSlide(
                slide_id="slide-2",
                layout="Detail",
                required=False,
                intent_tags=["detail"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="detail-slot",
                        anchor="DETAIL",
                        content_type="text",
                        required=False,
                        intent_tags=["detail"],
                    )
                ],
            ),
        ]
    )


def test_generate_document_dynamic_includes_title_card() -> None:
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())
    document, meta, records = orchestrator.generate_document(_build_source())

    assert document.cards, "dynamic mode should create cards"
    assert document.cards[0].content.title, "title card should be inserted when include_title_page"
    assert meta.mode == "dynamic"
    assert meta.policy_id is None
    assert records, "AI records should be collected"


def test_generate_document_static_resolves_slots() -> None:
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())
    document, meta, records = orchestrator.generate_document(
        _build_source(),
        mode="static",
        blueprint=_build_blueprint(),
        blueprint_ref={"path": "blueprint.json", "hash": "deadbeef", "template_source": "slide"},
    )

    assert any(card.meta.get("blueprint") for card in document.cards)
    assert meta.mode == "static"
    assert meta.policy_id is None
    assert records and records[0].batch_card_ids, "static mode should record batch responses"


def test_generate_document_static_records_prompt_overrides() -> None:
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())
    blueprint = _build_blueprint()
    override = StaticPromptOverride(
        slide_id=blueprint.slides[0].slide_id,
        slide_index=1,
        instructions="- 重要メッセージを先頭に配置",
        template_path=".pptx/extract/prompts/01_intro.md",
    )

    document, meta, records = orchestrator.generate_document(
        _build_source(),
        mode="static",
        blueprint=blueprint,
        blueprint_ref={"path": "blueprint.json", "hash": "deadbeef", "template_source": "slide"},
        prompt_overrides=[override],
    )

    assert meta.prompt_templates == [
        {
            "slide_id": blueprint.slides[0].slide_id,
            "slide_index": 1,
            "template_path": override.template_path,
        }
    ]
    assert records[0].prompt_template_path == override.template_path
    assert records[0].prompt_template_instructions == override.instructions


def test_build_body_blocks_variations() -> None:
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())

    bullet_payload = [
        {"type": "bullets", "items": [{"text": "Point A", "level": 1}, {"text": "Point B", "level": 0}]},
        {"type": "paragraph", "text": "summary"},
    ]
    blocks = orchestrator._build_body_blocks(bullet_payload)
    assert any(block.data and block.data.get("items") for block in blocks)

    fallback_blocks = orchestrator._build_body_blocks("- extra line\n- another line")
    assert fallback_blocks and fallback_blocks[0].type == "paragraph"


def test_build_note_entries_variations() -> None:
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())
    entry_with_notes = {
        "notes": [
            {"type": "note", "text": "explicit note"},
            "string note",
        ],
    }
    notes = orchestrator._build_note_entries(entry_with_notes)
    assert any(note.type == "note" for note in notes)

    entry_supporting_only = {
        "supporting_points": [
            {"statement": "supporting statement", "evidence_type": "url", "evidence_value": "https://example.com"}
        ]
    }
    supporting_notes = orchestrator._build_note_entries(entry_supporting_only)
    assert any("supporting statement" in note.text for note in supporting_notes)
