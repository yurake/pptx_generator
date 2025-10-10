"""SimpleRendererStep の拡張動作テスト。"""

from __future__ import annotations

import base64
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

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


def _load_placeholder_boxes(
    template_path: Path, layout_name: str
) -> dict[str, tuple[int, int, int, int, int]]:
    presentation = Presentation(template_path)
    layout = next(
        layout for layout in presentation.slide_layouts if layout.name == layout_name
    )
    placeholders: dict[str, tuple[int, int, int, int, int]] = {}
    for shape in layout.shapes:
        if getattr(shape, "is_placeholder", False):
            placeholders[shape.name] = (
                int(shape.left),
                int(shape.top),
                int(shape.width),
                int(shape.height),
                shape.placeholder_format.idx,
            )
    return placeholders


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


def _build_template_with_named_placeholders(tmp_path: Path):
    presentation = Presentation()

    two_content_layout = presentation.slide_layouts[3]
    left_placeholder_box: tuple[int, int, int, int] | None = None
    right_placeholder_box: tuple[int, int, int, int] | None = None

    supported_types = {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT}
    for shape in two_content_layout.shapes:
        if getattr(shape, "is_placeholder", False) and shape.placeholder_format.type in supported_types:
            if left_placeholder_box is None:
                shape.name = "Left Content Placeholder"
                left_placeholder_box = (
                    shape.left,
                    shape.top,
                    shape.width,
                    shape.height,
                )
            else:
                shape.name = "Right Content Placeholder"
                right_placeholder_box = (
                    shape.left,
                    shape.top,
                    shape.width,
                    shape.height,
                )

    picture_layout = presentation.slide_layouts[8]
    picture_placeholder_box: tuple[int, int, int, int] | None = None
    for shape in picture_layout.shapes:
        if getattr(shape, "is_placeholder", False) and shape.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
            shape.name = "Picture Content Placeholder"
            picture_placeholder_box = (
                shape.left,
                shape.top,
                shape.width,
                shape.height,
            )
            break

    template_path = tmp_path / "template_placeholders.pptx"
    presentation.save(template_path)

    assert left_placeholder_box and right_placeholder_box and picture_placeholder_box

    return (
        template_path,
        two_content_layout.name,
        picture_layout.name,
        left_placeholder_box,
        right_placeholder_box,
        picture_placeholder_box,
    )


def test_renderer_uses_layout_placeholder_names_for_anchors(tmp_path: Path) -> None:
    (
        template_path,
        two_content_layout_name,
        picture_layout_name,
        left_box,
        right_box,
        picture_box,
    ) = _build_template_with_named_placeholders(tmp_path)

    image_path = tmp_path / "placeholder_image.png"
    _write_dummy_png(image_path)

    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="Placeholder Anchor Test"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="table-slide",
                layout=two_content_layout_name,
                title="表スライド",
                tables=[
                    SlideTable(
                        id="table",
                        anchor="Left Content Placeholder",
                        columns=["ヘッダ1", "ヘッダ2"],
                        rows=[["A", "B"]],
                    )
                ],
            ),
            Slide(
                id="chart-slide",
                layout=two_content_layout_name,
                title="チャートスライド",
                charts=[
                    SlideChart(
                        id="chart",
                        anchor="Right Content Placeholder",
                        type="column",
                        categories=["X", "Y"],
                        series=[ChartSeries(name="Series", values=[1, 2])],
                    )
                ],
            ),
            Slide(
                id="image-slide",
                layout=picture_layout_name,
                title="画像スライド",
                images=[
                    SlideImage(
                        id="image",
                        anchor="Picture Content Placeholder",
                        source=str(image_path),
                    )
                ],
            ),
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    renderer = SimpleRendererStep(
        RenderingOptions(
            template_path=template_path,
            output_filename="placeholders.pptx",
            branding=BrandingConfig.default(),
        )
    )
    renderer.run(context)

    pptx_path = context.require_artifact("pptx_path")
    presentation = Presentation(pptx_path)

    table_slide = presentation.slides[0]
    table_shape = next(
        shape for shape in table_slide.shapes if getattr(shape, "has_table", False)
    )
    assert (
        table_shape.left,
        table_shape.top,
        table_shape.width,
        table_shape.height,
    ) == left_box

    chart_slide = presentation.slides[1]
    chart_shape = next(
        shape for shape in chart_slide.shapes if getattr(shape, "has_chart", False)
    )
    assert (
        chart_shape.left,
        chart_shape.top,
        chart_shape.width,
        chart_shape.height,
    ) == right_box

    image_slide = presentation.slides[2]
    picture_shape = next(
        shape
        for shape in image_slide.shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    )
    expected_left, expected_top, expected_width, expected_height = picture_box
    assert picture_shape.top == expected_top
    assert picture_shape.left >= expected_left
    assert picture_shape.width <= expected_width
    assert picture_shape.height <= expected_height
    expected_center_x = expected_left + expected_width // 2
    actual_center_x = picture_shape.left + picture_shape.width // 2
    assert abs(actual_center_x - expected_center_x) <= 2000


def test_renderer_handles_object_placeholders(tmp_path: Path) -> None:
    template_path = Path("samples/templates/templates2.pptx")
    placeholders = _load_placeholder_boxes(template_path, "Two Column Detail")
    assert "Body Left" in placeholders and "Body Right" in placeholders and "Logo" in placeholders

    image_path = Path("samples/assets/logo.png")
    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="Object Placeholder Test"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="object-placeholder",
                layout="Two Column Detail",
                title="配置テスト",
                tables=[
                    SlideTable(
                        id="table",
                        anchor="Body Left",
                        columns=["A", "B"],
                        rows=[["x", "y"]],
                    )
                ],
                charts=[
                    SlideChart(
                        id="chart",
                        anchor="Body Right",
                        type="column",
                        categories=["c1"],
                        series=[ChartSeries(name="s", values=[1])],
                    )
                ],
                images=[
                    SlideImage(
                        id="image",
                        anchor="Logo",
                        source=str(image_path),
                        sizing="stretch",
                    )
                ],
            )
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    renderer = SimpleRendererStep(
        RenderingOptions(
            template_path=template_path,
            output_filename="object-placeholder.pptx",
            branding=BrandingConfig.default(),
        )
    )
    renderer.run(context)

    presentation = Presentation(context.require_artifact("pptx_path"))
    slide = presentation.slides[0]

    table_shape = next(
        shape for shape in slide.shapes if getattr(shape, "has_table", False)
    )
    assert (
        int(table_shape.left),
        int(table_shape.top),
        int(table_shape.width),
        int(table_shape.height),
    ) == placeholders["Body Left"][:4]

    chart_shape = next(
        shape for shape in slide.shapes if getattr(shape, "has_chart", False)
    )
    assert (
        int(chart_shape.left),
        int(chart_shape.top),
        int(chart_shape.width),
        int(chart_shape.height),
    ) == placeholders["Body Right"][:4]

    picture_shape = next(
        shape
        for shape in slide.shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    )
    assert (
        int(picture_shape.left),
        int(picture_shape.top),
        int(picture_shape.width),
        int(picture_shape.height),
    ) == placeholders["Logo"][:4]

    placeholder_indices = {
        shape.placeholder_format.idx
        for shape in slide.shapes
        if getattr(shape, "is_placeholder", False)
    }
    assert placeholders["Body Left"][4] in placeholder_indices
    assert placeholders["Body Right"][4] in placeholder_indices
    assert placeholders["Logo"][4] in placeholder_indices
