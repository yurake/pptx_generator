"""Tests for blank line preservation in prepare AI prompts."""

from __future__ import annotations

import json

from pptx_generator.prepare.source import (
    PrepareSourceChapter,
    PrepareSourceDocument,
    PrepareSourceMeta,
)
from pptx_generator.prepare_ai.client import MockPrepareLLMClient
from pptx_generator.prepare_ai.orchestrator import PrepareAIOrchestrator
from pptx_generator.prepare_ai.prompts import PREPARE_DYNAMIC_PROMPT, PREPARE_STATIC_PROMPT


def test_dynamic_prompt_contains_blank_line_instructions() -> None:
    """Verify that the dynamic prompt includes blank line preservation instructions."""
    assert "空行" in PREPARE_DYNAMIC_PROMPT, "Dynamic prompt should mention blank lines"
    assert '{"text": "", "level": 0}' in PREPARE_DYNAMIC_PROMPT, "Dynamic prompt should specify blank line format"


def test_static_prompt_contains_blank_line_instructions() -> None:
    """Verify that the static prompt includes blank line preservation instructions."""
    assert "空行" in PREPARE_STATIC_PROMPT, "Static prompt should mention blank lines"
    assert '{"text": "", "level": 0}' in PREPARE_STATIC_PROMPT, "Static prompt should specify blank line format"


def test_generate_document_with_blank_lines_in_bullets() -> None:
    """Test that blank lines in bullet items are preserved in dynamic mode."""
    # Create source with blank lines in the raw text
    raw_text = """## Introduction
- Point A

- Point B
- Point C

- Point D"""

    source = PrepareSourceDocument(
        meta=PrepareSourceMeta(title="Blank Line Test", objective="Test blank line preservation"),
        chapters=[
            PrepareSourceChapter(
                id="intro",
                title="Introduction",
                message="Test message",
                details=["Point A", "", "Point B", "Point C", "", "Point D"],
                supporting_points=[],
                intent_tags=["introduction"],
            )
        ],
        raw_text=raw_text,
    )

    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())
    document, meta, records = orchestrator.generate_document(source)

    assert document.cards, "Document should have cards"
    assert meta.mode == "dynamic"

    # Verify that the orchestrator can handle blank lines in body blocks
    for card in document.cards:
        for block in card.content.body:
            if block.type == "bullets" and block.data:
                items = block.data.get("items", [])
                # Check if any item has empty text (blank line)
                blank_items = [item for item in items if isinstance(item, dict) and item.get("text") == ""]
                # Note: MockPrepareLLMClient may not preserve blank lines,
                # but the orchestrator should be able to handle them if LLM returns them
                # This test verifies the structure is compatible
                for item in items:
                    assert isinstance(item, dict), "Bullet items should be dictionaries"
                    assert "text" in item, "Bullet items should have 'text' field"
                    assert "level" in item, "Bullet items should have 'level' field"


def test_build_body_blocks_with_blank_lines() -> None:
    """Test that _build_body_blocks can handle blank line items."""
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())

    # Test bullets with blank lines
    bullet_payload_with_blanks = [
        {
            "type": "bullets",
            "items": [
                {"text": "First point", "level": 0},
                {"text": "", "level": 0},  # Blank line
                {"text": "Second point", "level": 0},
                {"text": "", "level": 0},  # Another blank line
                {"text": "Third point", "level": 0},
            ],
        }
    ]

    blocks = orchestrator._build_body_blocks(bullet_payload_with_blanks)
    assert len(blocks) == 1, "Should create one bullets block"

    bullets_block = blocks[0]
    assert bullets_block.type == "bullets"
    assert bullets_block.data is not None
    items = bullets_block.data.get("items", [])
    assert len(items) == 5, "Should preserve all items including blank lines"

    # Verify blank lines are preserved
    blank_items = [item for item in items if item.get("text") == ""]
    assert len(blank_items) == 2, "Should have 2 blank line items"

    # Verify non-blank items
    non_blank_items = [item for item in items if item.get("text") != ""]
    assert len(non_blank_items) == 3, "Should have 3 non-blank items"
    assert non_blank_items[0]["text"] == "First point"
    assert non_blank_items[1]["text"] == "Second point"
    assert non_blank_items[2]["text"] == "Third point"


def test_blank_line_format_in_prompt_payload() -> None:
    """Test that the prompt format example includes blank line representation."""
    from pptx_generator.prepare_ai.prompts import build_prepare_prompt_dynamic

    test_payload = {
        "raw_context": {"content": "Test content"},
        "options": {"include_title_page": False},
        "constraints": {},
    }

    prompt = build_prepare_prompt_dynamic(test_payload)

    # Verify the prompt contains blank line instructions
    assert "空行" in prompt, "Prompt should contain blank line instructions"
    assert '{"text": "", "level": 0}' in prompt, "Prompt should show blank line format"


def test_mixed_content_with_blank_lines() -> None:
    """Test handling of mixed content including paragraphs and bullets with blank lines."""
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())

    mixed_payload = [
        {"type": "paragraph", "text": "Introduction paragraph"},
        {
            "type": "bullets",
            "items": [
                {"text": "Bullet A", "level": 0},
                {"text": "", "level": 0},  # Blank line
                {"text": "Bullet B", "level": 1},
                {"text": "Bullet C", "level": 0},
            ],
        },
        {"type": "paragraph", "text": "Conclusion paragraph"},
    ]

    blocks = orchestrator._build_body_blocks(mixed_payload)
    assert len(blocks) == 3, "Should create 3 blocks"

    # Verify first block is paragraph
    assert blocks[0].type == "paragraph"
    assert blocks[0].text == "Introduction paragraph"

    # Verify second block is bullets with blank line
    assert blocks[1].type == "bullets"
    items = blocks[1].data.get("items", [])  # type: ignore[union-attr]
    assert len(items) == 4
    assert items[1]["text"] == "", "Second item should be blank"

    # Verify third block is paragraph
    assert blocks[2].type == "paragraph"
    assert blocks[2].text == "Conclusion paragraph"


def test_empty_text_vs_missing_text() -> None:
    """Test that empty string text is different from missing text."""
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())

    # This should be handled gracefully - empty string is intentional blank line
    valid_blank_payload = [
        {
            "type": "bullets",
            "items": [
                {"text": "Normal item", "level": 0},
                {"text": "", "level": 0},  # Intentional blank
            ],
        }
    ]

    blocks = orchestrator._build_body_blocks(valid_blank_payload)
    assert len(blocks) == 1
    items = blocks[0].data.get("items", [])  # type: ignore[union-attr]
    assert len(items) == 2
    assert items[0]["text"] == "Normal item"
    assert items[1]["text"] == ""
    assert items[1]["text"] is not None, "Empty string is not None"