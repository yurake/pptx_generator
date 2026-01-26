from pptx_generator.prepare.models import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
)
from pptx_generator.pipeline.draft_structuring.slide_elements import assign_text_content


def _build_card(body_blocks: list[PrepareBodyBlock]) -> PrepareCard:
    return PrepareCard(
        card_id="card-1",
        role=PrepareCardRole(story_phase="introduction"),
        content=PrepareCardContent(title="Sample", body=body_blocks),
    )


def test_assign_text_content_keeps_bullets_only_compat() -> None:
    card = _build_card(
        [
            PrepareBodyBlock(
                type="bullets",
                items=[
                    {"text": "要点1", "level": 0},
                    {"text": "要点2", "level": 1},
                ],
            )
        ]
    )
    elements: dict[str, object] = {}
    lines = list(card.iter_body_text())

    assign_text_content(elements, "body", "body", card, lines)

    assert elements["body"] == [
        {"text": "要点1", "level": 0},
        {"text": "要点2", "level": 1},
    ]


def test_assign_text_content_uses_typed_blocks_for_mixed() -> None:
    card = _build_card(
        [
            PrepareBodyBlock(type="paragraph", text="段落1\n\n段落2"),
            PrepareBodyBlock(type="bullets", items=[{"text": "要点1", "level": 0}]),
            PrepareBodyBlock(type="custom", text="カスタム", description="説明"),
        ]
    )
    elements: dict[str, object] = {}
    lines = list(card.iter_body_text())

    assign_text_content(elements, "body", "body", card, lines)

    assert elements["body"] == [
        {"type": "paragraph", "text": "段落1\n\n段落2"},
        {"type": "bullets", "items": [{"text": "要点1", "level": 0}]},
        {"type": "custom", "text": "カスタム", "description": "説明"},
    ]
