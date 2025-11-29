from pptx_generator.models import FontSpec, TextFramePadding, TextboxParagraph
from pptx_generator.utils.text_capacity import estimate_text_capacity


def _font(size: float) -> FontSpec:
    return FontSpec(name="Test", size_pt=size, color_hex="#000000")


def test_estimate_text_capacity_scales_with_dimensions() -> None:
    capacity = estimate_text_capacity(width_in=5, height_in=3, font=_font(18.0))

    assert capacity.max_lines > 0
    assert capacity.chars_per_line > 0
    assert capacity.total_chars == capacity.max_lines * capacity.chars_per_line


def test_estimate_text_capacity_respects_font_size() -> None:
    small_font = estimate_text_capacity(width_in=4, height_in=3, font=_font(16.0))
    large_font = estimate_text_capacity(width_in=4, height_in=3, font=_font(28.0))

    assert small_font.total_chars > large_font.total_chars


def test_estimate_text_capacity_accounts_for_padding_and_indents() -> None:
    baseline = estimate_text_capacity(width_in=5, height_in=2, font=_font(18.0))

    padded = estimate_text_capacity(
        width_in=5,
        height_in=2,
        font=_font(18.0),
        paragraph=TextboxParagraph(left_indent_in=0.5, right_indent_in=0.5),
        padding=TextFramePadding(left_in=0.5, right_in=0.5, top_in=0.25, bottom_in=0.25),
    )

    assert padded.total_chars < baseline.total_chars
