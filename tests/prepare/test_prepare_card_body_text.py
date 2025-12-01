from pptx_generator.prepare.models import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
)


def test_iter_body_text_handles_multiple_block_types() -> None:
    body_blocks = [
        PrepareBodyBlock(type="text", text="  first line\n\nsecond line  "),
        PrepareBodyBlock(
            type="list",
            data={
                "items": [
                    "  bullet text  ",
                    {"text": "  nested text  ", "level": 2},
                    {},
                ]
            }
        ),
        PrepareBodyBlock(
            type="table",
            rows=[
                [" cell1 ", " ", "cell2"],
                ["", ""],
                [f"long {'a' * 205}"],
            ]
        ),
        PrepareBodyBlock(type="note", description="  desc line  "),
    ]
    card = PrepareCard(
        card_id="card-1",
        role=PrepareCardRole(story_phase="introduction"),
        content=PrepareCardContent(title="Sample", body=body_blocks),
    )

    lines = list(card.iter_body_text())

    assert lines == [
        "first line",
        "second line",
        "bullet text",
        "    nested text",
        "cell1 | cell2",
        f"{'long ' + 'a' * 195}",
        f"{'a' * 10}",
        "desc line",
    ]
