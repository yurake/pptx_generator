"""SimpleRendererStep の拡張動作テスト。"""

from __future__ import annotations

import base64
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE

from pptx_generator.models import (
    ChartOptions,
    ChartSeries,
    JobAuth,
    JobMeta,
    JobSpec,
    Slide,
    SlideBullet,
    SlideChart,
    SlideImage,
    SlideTable,
    TableStyle,
)
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.renderer import RenderingOptions, SimpleRendererStep
from pptx_generator.settings import BrandingConfig, BrandingFont


def _write_dummy_png(path: Path) -> None:
    payload = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    path.write_bytes(payload)


def test_renderer_renders_rich_content(tmp_path: Path) -> None:
    image_path = tmp_path / "image.png"
    _write_dummy_png(image_path)

    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="提案"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                title="サンプルタイトル",
                bullets=[
                    SlideBullet(id="b1", text="箇条書き", level=0, font=None),
                ],
                images=[
                    SlideImage(
                        id="img",
                        source=str(image_path),
                        left_in=6.0,
                        top_in=1.5,
                        width_in=3.0,
                        height_in=3.0,
                    )
                ],
                tables=[
                    SlideTable(
                        id="tbl",
                        columns=["指標", "値"],
                        rows=[["A", 10], ["B", 20]],
                        style=TableStyle(header_fill="#334455", zebra=True),
                    )
                ],
                charts=[
                    SlideChart(
                        id="chart",
                        type="column",
                        categories=["Before", "After"],
                        series=[
                            ChartSeries(name="効果", values=[10, 5], color_hex="#123456"),
                        ],
                        options=ChartOptions(data_labels=True, y_axis_format="0%"),
                    )
                ],
            )
        ],
    )

    branding = BrandingConfig(
        heading_font=BrandingFont(name="HeadingBrand", size_pt=30.0, color_hex="#101010"),
        body_font=BrandingFont(name="BodyBrand", size_pt=20.0, color_hex="#202020"),
        primary_color="#445566",
        secondary_color="#DDEEFF",
        accent_color="#CC5500",
        background_color="#FFFFFF",
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    renderer = SimpleRendererStep(
        RenderingOptions(output_filename="out.pptx", branding=branding)
    )
    renderer.run(context)

    pptx_path = context.artifacts["pptx_path"]
    presentation = Presentation(pptx_path)
    slide = presentation.slides[0]

    pictures = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert pictures, "画像が描画されていること"

    tables = [shape for shape in slide.shapes if getattr(shape, "has_table", False)]
    assert tables, "テーブルが描画されていること"
    table = tables[0].table

    header_cell = table.rows[0].cells[0]
    assert header_cell.fill.fore_color.rgb == RGBColor.from_string("334455")
    data_cell = table.rows[2].cells[0]
    assert data_cell.fill.fore_color.rgb == RGBColor.from_string("DDEEFF")

    text_paragraph = None
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False):
            for paragraph in shape.text_frame.paragraphs:
                if paragraph.text == "箇条書き":
                    text_paragraph = paragraph
                    break
        if text_paragraph:
            break
    assert text_paragraph is not None
    assert text_paragraph.font.name == "BodyBrand"

    charts = [shape for shape in slide.shapes if getattr(shape, "has_chart", False)]
    assert charts, "チャートが描画されていること"
    chart = charts[0].chart
    plot = chart.plots[0]
    assert plot.has_data_labels is True
    assert plot.data_labels.show_value is True
    if hasattr(chart, "value_axis"):
        assert chart.value_axis.tick_labels.number_format == "0%"
    series = chart.series[0]
    assert series.format.fill.fore_color.rgb == RGBColor.from_string("123456")
