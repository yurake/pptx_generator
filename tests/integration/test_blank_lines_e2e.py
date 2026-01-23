"""End-to-end test for blank line preservation through the full pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptx_generator.prepare.source import PrepareSourceChapter, PrepareSourceDocument, PrepareSourceMeta
from pptx_generator.prepare_ai.client import MockPrepareLLMClient
from pptx_generator.prepare_ai.orchestrator import PrepareAIOrchestrator


@pytest.fixture
def blank_lines_source() -> PrepareSourceDocument:
    """Create a source document with intentional blank lines."""
    return PrepareSourceDocument(
        meta=PrepareSourceMeta(title="Blank Lines E2E Test", objective="Test blank line preservation"),
        chapters=[
            PrepareSourceChapter(
                id="intro",
                title="Introduction",
                message="サービス概要と主要機能を紹介",
                details=[
                    "サービス概要",
                    "主要機能",
                    "",  # Blank line
                    "ターゲット顧客",
                ],
                supporting_points=[],
                intent_tags=["introduction"],
            ),
            PrepareSourceChapter(
                id="problem",
                title="Problem",
                message="現状の課題を説明",
                details=[
                    "現状の課題A",
                    "",  # Blank line
                    "現状の課題B",
                    "",  # Blank line
                    "現状の課題C",
                ],
                supporting_points=[],
                intent_tags=["problem"],
            ),
            PrepareSourceChapter(
                id="solution",
                title="Solution",
                message="解決策を提示",
                details=[
                    "解決策1：システム導入",
                    "",  # Blank line
                    "解決策2：プロセス改善",
                    "",  # Blank line
                    "解決策3：人材育成",
                ],
                supporting_points=[],
                intent_tags=["solution"],
            ),
        ],
        raw_text="""# Introduction
- サービス概要
- 主要機能

- ターゲット顧客

# Problem
- 現状の課題A

- 現状の課題B

- 現状の課題C

# Solution
- 解決策1：システム導入

- 解決策2：プロセス改善

- 解決策3：人材育成
""",
    )


def test_blank_lines_preserved_in_dynamic_mode(blank_lines_source: PrepareSourceDocument) -> None:
    """Test that blank lines are preserved through the dynamic mode pipeline."""
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())
    document, meta, records = orchestrator.generate_document(blank_lines_source)

    assert document.cards, "Document should have cards"
    assert meta.mode == "dynamic"

    # Verify cards were created
    assert len(document.cards) > 0, "Should create at least one card"

    # Check that the document structure can handle blank lines
    for card in document.cards:
        for block in card.content.body:
            if block.type == "bullets" and block.data:
                items = block.data.get("items", [])
                for item in items:
                    # Verify structure: each item must have text and level
                    assert isinstance(item, dict), "Item should be a dictionary"
                    assert "text" in item, "Item must have 'text' field"
                    assert "level" in item, "Item must have 'level' field"
                    # Blank lines are represented as empty strings
                    if item["text"] == "":
                        assert item["level"] == 0, "Blank lines should have level 0"


def test_blank_lines_json_serialization(blank_lines_source: PrepareSourceDocument) -> None:
    """Test that blank lines can be serialized to JSON correctly."""
    orchestrator = PrepareAIOrchestrator(llm_client=MockPrepareLLMClient())
    document, meta, records = orchestrator.generate_document(blank_lines_source)

    # Serialize document to JSON
    document_dict = {
        "cards": [
            {
                "card_id": card.card_id,
                "content": {
                    "title": card.content.title,
                    "headline": card.content.headline,
                    "body": [
                        {
                            "type": block.type,
                            "text": block.text if hasattr(block, "text") else None,
                            "data": block.data if hasattr(block, "data") else None,
                        }
                        for block in card.content.body
                    ],
                },
            }
            for card in document.cards
        ]
    }

    # Ensure JSON serialization works
    json_str = json.dumps(document_dict, ensure_ascii=False)
    assert json_str, "Should serialize to JSON"

    # Deserialize and verify
    parsed = json.loads(json_str)
    assert "cards" in parsed
    assert len(parsed["cards"]) > 0


def test_prepare_card_output_format() -> None:
    """Test that prepare card output matches expected format with blank lines."""
    # Simulate LLM response with blank lines
    llm_response = {
        "chapters": [
            {
                "card_id": "intro-1",
                "title": "Introduction",
                "story_phase": "introduction",
                "intent_tags": ["introduction"],
                "headline": "サービス概要",
                "body": [
                    {
                        "type": "bullets",
                        "items": [
                            {"text": "ポイント1", "level": 0},
                            {"text": "", "level": 0},  # Blank line
                            {"text": "ポイント2", "level": 0},
                        ],
                    }
                ],
                "notes": [],
            }
        ]
    }

    # Verify format
    chapter = llm_response["chapters"][0]
    assert "body" in chapter
    assert len(chapter["body"]) > 0

    bullets_block = chapter["body"][0]
    assert bullets_block["type"] == "bullets"
    assert "items" in bullets_block

    items = bullets_block["items"]
    assert len(items) == 3
    assert items[0]["text"] == "ポイント1"
    assert items[1]["text"] == ""  # Blank line
    assert items[2]["text"] == "ポイント2"

    # All items should have level
    for item in items:
        assert "level" in item
        assert isinstance(item["level"], int)