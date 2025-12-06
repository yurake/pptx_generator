"""SimpleAnalyzerStep の診断結果を検証するテスト。"""

from __future__ import annotations

import base64
import json

import pytest

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Inches, Pt

from pptx_generator.prepare import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareDocument,
    PrepareStoryContext,
)
from pptx_generator.models import (
    DraftDocument,
    DraftSection,
    DraftSlideCard,
    FontSpec,
    JobAuth,
    JobMeta,
    JobSpec,
    Slide,
    SlideBullet,
    SlideBulletGroup,
    SlideImage,
    SlideTextbox,
)
from pptx_generator.pipeline import (
    AnalyzerOptions,
    MappingOptions,
    MappingStep,
    PipelineContext,
    RenderingOptions,
    SimpleAnalyzerStep,
    SimpleRendererStep,
)
from pptx_generator.generate_ready import generate_ready_to_jobspec
from pptx_generator.pipeline.analyzer import BulletParagraphResolver, ShapeSnapshot, SlideSnapshot


def _group(*bullets: SlideBullet, anchor: str | None = None) -> SlideBulletGroup:
    return SlideBulletGroup(anchor=anchor, items=list(bullets))


def _write_dummy_png(path) -> None:
    # 1px x 1px の透明 PNG
    payload = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    path.write_bytes(payload)


def _render_spec(spec: JobSpec, workdir, template_path=None) -> PipelineContext:
    context = PipelineContext(spec=spec, workdir=workdir)
    options = RenderingOptions(output_filename="test.pptx")
    if template_path is not None:
        options.template_path = template_path
    renderer = SimpleRendererStep(options)
    renderer.run(context)
    return context


def _attach_minimal_draft_document(context: PipelineContext, spec: JobSpec) -> None:
    cards = [
        DraftSlideCard(ref_id=slide.id, order=index, layout_hint=slide.layout)
        for index, slide in enumerate(spec.slides, start=1)
    ]
    section = DraftSection(name="auto", order=1, slides=cards)
    context.add_artifact("draft_document", DraftDocument(sections=[section]))


def test_simple_analyzer_detects_quality_issues(tmp_path) -> None:
    image_path = tmp_path / "image.png"
    _write_dummy_png(image_path)

    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="テスト案件",
            client="Zeta",
            author="営業部",
            created_at="2025-10-05",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                title="テストスライド",
                bullets=[
                    _group(
                        SlideBullet(
                            id="bullet-1",
                            text="本文",
                            level=4,
                            font=FontSpec(
                                name="Meiryo UI",
                                size_pt=12.0,
                                color_hex="#FFFFFF",
                            ),
                        )
                    )
                ],
                images=[
                    SlideImage(
                        id="img-1",
                        source=str(image_path),
                        left_in=0.1,
                        top_in=0.2,
                        width_in=9.5,
                        height_in=7.0,
                    )
                ],
            )
        ],
    )

    context = _render_spec(spec, tmp_path)
    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(
            min_font_size=16.0,
            default_font_size=16.0,
            max_bullet_level=3,
            default_font_color="#CCCCCC",
            preferred_text_color="#005BAC",
            background_color="#FFFFFF",
            margin_in=0.5,
        )
    )

    analyzer.run(context)

    analysis_path = context.require_artifact("analysis_path")
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))

    issue_types = {issue["type"] for issue in payload["issues"]}
    assert {
        "margin",
        "font_min",
        "contrast_low",
        "bullet_depth",
        "layout_consistency",
        "grid_misaligned",
    } <= issue_types

    fix_types = {fix["type"] for fix in payload["fixes"]}
    assert {"move", "font_raise", "color_adjust", "bullet_cap", "bullet_reindent"} <= fix_types

    margin_issue = next(issue for issue in payload["issues"] if issue["type"] == "margin")
    assert margin_issue["fix"]["payload"]

    layout_issue = next(issue for issue in payload["issues"] if issue["type"] == "layout_consistency")
    assert layout_issue["fix"]["payload"]["level"] == 0
    contrast_issue = next(issue for issue in payload["issues"] if issue["type"] == "contrast_low")
    assert contrast_issue["metrics"]["required_ratio"] == pytest.approx(4.5)
    assert contrast_issue["metrics"]["font_size_pt"] == pytest.approx(12.0)


def test_analyzer_updates_mapping_log(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="Analyzer 連携テスト",
            client="Zeta",
            author="営業部",
            created_at="2025-10-21",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                title="概要",
                bullets=[
                    _group(
                        SlideBullet(
                            id="bullet-1",
                            text="最初のポイント",
                            level=0,
                        )
                    )
                ],
            )
        ],
    )

    mapping_context = PipelineContext(spec=spec, workdir=tmp_path)
    _attach_minimal_draft_document(mapping_context, spec)
    prepare_doc = PrepareDocument(
        prepare_id="prepare-test",
        cards=[
            PrepareCard(
                card_id="slide-1",
                order=1,
                role=PrepareCardRole(story_phase="introduction", intent_tags=["intro"]),
                content=PrepareCardContent(
                    headline="概要",
                    body=[PrepareBodyBlock(type="paragraph", text="最初のポイント")],
                ),
            )
        ],
        story_context=PrepareStoryContext(chapters=[]),
    )
    mapping_context.add_artifact("prepare_document", prepare_doc)
    mapping_step = MappingStep(MappingOptions(output_dir=tmp_path))
    mapping_step.run(mapping_context)

    generate_ready = mapping_context.artifacts["generate_ready"]
    render_spec = generate_ready_to_jobspec(generate_ready)
    render_context = PipelineContext(
        spec=render_spec,
        workdir=tmp_path,
        artifacts=dict(mapping_context.artifacts),
    )

    renderer = SimpleRendererStep(RenderingOptions(output_filename="rm031.pptx"))
    renderer.run(render_context)

    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(
            min_font_size=40.0,
            default_font_size=18.0,
            max_bullet_level=3,
            default_font_color="#777777",
            preferred_text_color="#005BAC",
            background_color="#FFFFFF",
        )
    )
    analyzer.run(render_context)

    mapping_log_path = tmp_path / "mapping_log.json"
    payload = json.loads(mapping_log_path.read_text(encoding="utf-8"))

    slide_summary = payload["slides"][0]["analyzer"]
    assert slide_summary["issue_count"] >= 1
    assert "font_min" in slide_summary["issue_counts_by_type"]
    issue_types = {issue["issue_type"] for issue in slide_summary["issues"]}
    assert "font_min" in issue_types
    target_slide_ids = {issue["target"].get("slide_id") for issue in slide_summary["issues"]}
    assert spec.slides[0].id in target_slide_ids

    meta = payload["meta"]
    assert meta["analyzer_issue_count"] == slide_summary["issue_count"]
    assert meta["analyzer_issue_counts_by_type"]["font_min"] == slide_summary["issue_counts_by_type"]["font_min"]


def test_margin_check_respects_actual_slide_size(tmp_path) -> None:
    template_path = tmp_path / "widescreen.pptx"
    template = Presentation()
    template.slide_width = Inches(13.333333)
    template.slide_height = Inches(7.5)
    template.save(template_path)

    image_path = tmp_path / "wide.png"
    _write_dummy_png(image_path)

    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="ワイドスライド",
            client="Zeta",
            author="営業部",
            created_at="2025-10-08",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="wide-1",
                layout="Title and Content",
                images=[
                    SlideImage(
                        id="wide-img",
                        source=str(image_path),
                        left_in=1.0,
                        top_in=1.0,
                        width_in=11.0,
                        height_in=5.5,
                    )
                ],
            )
        ],
    )

    context = _render_spec(spec, tmp_path, template_path=template_path)
    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(
            margin_in=0.5,
            grid_size_in=0.125,
            grid_tolerance_in=0.02,
        )
    )

    analyzer.run(context)

    analysis_path = context.require_artifact("analysis_path")
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))

    margin_issues = [issue for issue in payload["issues"] if issue["type"] == "margin"]
    assert not margin_issues


def test_simple_analyzer_allows_large_text_with_lower_contrast(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="コントラスト調整テスト",
            client="Zeta",
            author="営業部",
            created_at="2025-10-07",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-large",
                layout="Title and Content",
                bullets=[
                    _group(
                        SlideBullet(
                            id="bullet-large",
                            text="セカンダリカラーの本文",
                            level=0,
                            font=FontSpec(
                                name="Meiryo UI",
                                size_pt=24.0,
                                color_hex="#0097A7",
                            ),
                        )
                    )
                ],
            )
        ],
    )

    context = _render_spec(spec, tmp_path)
    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(
            min_font_size=16.0,
            default_font_size=16.0,
            max_bullet_level=3,
            default_font_color="#333333",
            preferred_text_color="#005BAC",
            background_color="#FFFFFF",
            large_text_threshold_pt=18.0,
            large_text_min_contrast=3.0,
        )
    )

    analyzer.run(context)

    analysis_path = context.require_artifact("analysis_path")
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))

    issue_types = {issue["type"] for issue in payload["issues"]}
    assert "contrast_low" not in issue_types


def test_analyzer_outputs_structure_snapshot(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="スナップショット検証",
            client="Zeta",
            author="営業部",
            created_at="2025-10-17",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-structure",
                layout="Title and Content",
                bullets=[
                    _group(
                        SlideBullet(
                            id="bullet-structure",
                            text="アンカー検証",
                            level=1,
                        ),
                    )
                ],
            )
        ],
    )

    context = _render_spec(spec, tmp_path)
    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(snapshot_output_filename="analysis_snapshot.json")
    )

    analyzer.run(context)

    snapshot_path = context.require_artifact("analyzer_snapshot_path")
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0.0"
    assert payload["slides"], "スナップショットにスライドが含まれていません"
    slide_entry = payload["slides"][0]
    assert slide_entry["slide_id"] == "slide-structure"
    assert slide_entry["layout"] == "Title and Content"
    assert "placeholders" in slide_entry
    placeholder_paragraphs = [
        entry
        for entry in slide_entry["placeholders"]
        if entry.get("paragraphs")
    ]
    assert placeholder_paragraphs, "プレースホルダーに段落情報が含まれていません"
    paragraph_texts = [
        paragraph["text"]
        for entry in placeholder_paragraphs
        for paragraph in entry["paragraphs"]
        if paragraph["text"]
    ]
    assert paragraph_texts, "段落テキストが空です"
    assert "アンカー検証" in paragraph_texts


def test_slide_snapshot_from_slide_extracts_metadata() -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])

    body_shape = slide.shapes.placeholders[1]
    body_shape.name = "Body"
    text_frame = body_shape.text_frame
    text_frame.margin_left = Inches(0.2)
    text_frame.margin_top = Inches(0.1)
    paragraph = text_frame.paragraphs[0]
    paragraph.text = "本文"
    paragraph.level = 0
    paragraph.font.size = Pt(24)
    paragraph.font.name = "Calibri"
    paragraph.font.bold = True
    paragraph.font.color.rgb = RGBColor(0x12, 0x34, 0x56)
    paragraph.line_spacing = 36
    paragraph.space_before = Pt(6)
    paragraph.space_after = Pt(12)

    textbox = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(4), Inches(1))
    textbox.name = "anchored-shape"
    textbox.text_frame.text = "アンカー"
    additional = textbox.text_frame.add_paragraph()
    additional.text = "サブ"

    snapshot = SlideSnapshot.from_slide(slide, 0)
    assert snapshot.index == 0
    assert snapshot.body_placeholder_id is not None

    body_snapshot = snapshot.shape_by_id(snapshot.body_placeholder_id)
    assert body_snapshot is not None
    assert body_snapshot.is_placeholder
    assert body_snapshot.placeholder_type is not None
    assert body_snapshot.text_frame_padding is not None
    assert pytest.approx(body_snapshot.text_frame_padding["left_in"], rel=1e-3) == 0.2
    assert snapshot.find_shape_by_name("anchored-shape") is not None

    resolver = BulletParagraphResolver(snapshot)
    fallback = resolver.resolve(None)
    assert fallback is not None
    assert fallback.text == "本文"

    anchored_first = resolver.resolve("anchored-shape")
    anchored_second = resolver.resolve("anchored-shape")
    assert anchored_first is not None and anchored_first.text == "アンカー"
    assert anchored_second is not None and anchored_second.text == "サブ"


def test_analyzer_locates_shapes_via_snapshot_helpers(tmp_path) -> None:
    picture_shape = ShapeSnapshot(
        shape_id=101,
        name="anchor-picture",
        shape_type=int(MSO_SHAPE_TYPE.PICTURE),
        left_in=1.0,
        top_in=1.5,
        width_in=2.5,
        height_in=1.0,
    )
    textbox_shape = ShapeSnapshot(
        shape_id=102,
        name="anchor-textbox",
        shape_type=int(MSO_SHAPE_TYPE.TEXT_BOX),
        left_in=0.5,
        top_in=0.75,
        width_in=3.5,
        height_in=1.2,
    )
    placeholder_shape = ShapeSnapshot(
        shape_id=103,
        name="textbox-2",
        shape_type=int(MSO_SHAPE_TYPE.PLACEHOLDER),
        left_in=0.4,
        top_in=1.0,
        width_in=3.0,
        height_in=1.1,
        is_placeholder=True,
        placeholder_type=int(PP_PLACEHOLDER.BODY),
    )
    snapshot = SlideSnapshot(
        index=0,
        shapes=[picture_shape, textbox_shape, placeholder_shape],
        body_placeholder_id=placeholder_shape.shape_id,
    )

    analyzer = SimpleAnalyzerStep()
    image_spec = SlideImage(
        id="image-1",
        source=str((tmp_path / "dummy.png").as_posix()),
        anchor="anchor-picture",
    )
    assert analyzer._locate_image_shape(snapshot, image_spec) is picture_shape

    fallback_image_spec = SlideImage(
        id="image-2",
        source=str((tmp_path / "dummy2.png").as_posix()),
    )
    assert analyzer._locate_image_shape(snapshot, fallback_image_spec) is picture_shape

    textbox_spec = SlideTextbox(id="textbox-1", text="内容", anchor="anchor-textbox")
    assert analyzer._locate_textbox_shape(snapshot, textbox_spec) is textbox_shape

    fallback_textbox = SlideTextbox(id="textbox-2", text="詳細")
    assert analyzer._locate_textbox_shape(snapshot, fallback_textbox) is placeholder_shape
