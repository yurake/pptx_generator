from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from pptx_generator.pipeline.text_edit import overwrite_text_frame_preserving_style


def test_overwrite_text_frame_preserves_run_style() -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    textbox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))

    text_frame = textbox.text_frame
    paragraph = text_frame.paragraphs[0]
    paragraph.text = "before"
    paragraph.level = 1
    paragraph.line_spacing = Pt(30)
    paragraph.space_after = Pt(6)
    paragraph.alignment = None
    run = paragraph.runs[0]
    run.font.name = "Calibri"
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x12, 0x34, 0x56)
    text_frame.word_wrap = False

    overwrite_text_frame_preserving_style(text_frame, "after line1\nafter line2")

    assert [p.text for p in text_frame.paragraphs] == ["after line1", "after line2"]
    for para in text_frame.paragraphs:
        assert para.level == 1
        assert para.line_spacing == Pt(30)
        assert para.space_after == Pt(6)
        assert para.runs[0].font.name == "Calibri"
        assert para.runs[0].font.size == Pt(18)
        assert para.runs[0].font.bold is True
        assert para.runs[0].font.color.rgb == RGBColor(0x12, 0x34, 0x56)
    assert text_frame.word_wrap is False
