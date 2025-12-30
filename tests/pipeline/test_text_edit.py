from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from pptx_generator.pipeline.text_edit import apply_shape_text_edits, overwrite_text_frame_preserving_style
from pptx_generator.pipeline.analyzer.snapshot import table_cell_shape_id


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


def test_apply_shape_text_edits_updates_textbox(tmp_path) -> None:
    pptx_path = tmp_path / "input.pptx"
    output_path = tmp_path / "output.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    textbox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    paragraph = textbox.text_frame.paragraphs[0]
    paragraph.text = "before"
    paragraph.runs[0].font.name = "Calibri"
    presentation.save(pptx_path)

    applied, missing = apply_shape_text_edits(
        pptx_path,
        [{"shape_id": textbox.shape_id, "contents": "after"}],
        output_path=output_path,
    )

    assert applied == 1
    assert missing == []
    reloaded = Presentation(output_path)
    reloaded_shape = next(s for s in reloaded.slides[0].shapes if s.shape_id == textbox.shape_id)
    assert reloaded_shape.text == "after"


def test_apply_shape_text_edits_updates_table_cell(tmp_path) -> None:
    pptx_path = tmp_path / "input_table.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    table_shape = slide.shapes.add_table(2, 2, Inches(1), Inches(1), Inches(4), Inches(2))
    table = table_shape.table
    table.cell(1, 0).text = "cell"
    presentation.save(pptx_path)

    target_id = table_cell_shape_id(int(table_shape.shape_id), 1, 0)
    applied, missing = apply_shape_text_edits(
        pptx_path,
        [{"shape_id": target_id, "contents": "updated"}],
    )

    assert applied == 1
    assert missing == []
    reloaded = Presentation(pptx_path)
    assert reloaded.slides[0].shapes[0].table.cell(1, 0).text == "updated"
