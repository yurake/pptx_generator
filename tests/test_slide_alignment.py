"""Slide ID アライナーのユニットテスト。"""

from __future__ import annotations

from pptx_generator.brief.models import BriefCard, BriefDocument, BriefStoryInfo
from pptx_generator.models import (ContentApprovalDocument, ContentElements,
                                   ContentSlide, JobAuth, JobMeta, JobSpec,
                                   Slide)
from pptx_generator.pipeline.slide_alignment import (SlideIdAligner,
                                                     SlideIdAlignerOptions)


def _build_spec() -> JobSpec:
    return JobSpec(
        meta=JobMeta(
            schema_version="1.0",
            title="サンプル提案",
            client="Example Corp",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(id="intro-slide", layout="Title", title="イントロダクション"),
            Slide(id="solution-slide", layout="Content", title="解決策の概要"),
        ],
    )


def _build_brief() -> BriefDocument:
    return BriefDocument(
        brief_id="sample",
        cards=[
            BriefCard(
                card_id="intro",
                chapter="イントロダクション",
                message="現状と課題の共有",
                narrative=["イントロの詳細"],
                supporting_points=[],
                story=BriefStoryInfo(phase="introduction"),
                intent_tags=["introduction"],
            ),
            BriefCard(
                card_id="solution",
                chapter="解決策",
                message="解決策の要点",
                narrative=["提案内容"],
                supporting_points=[],
                story=BriefStoryInfo(phase="solution"),
                intent_tags=["solution"],
            ),
        ],
    )


def _build_content_document() -> ContentApprovalDocument:
    return ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
            ContentSlide(id="solution", intent="solution", elements=ContentElements(title="解決策")),
        ]
    )


def test_slide_id_aligner_applies_matching() -> None:
    spec = _build_spec()
    brief = _build_brief()
    document = _build_content_document()
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.1))

    result = aligner.align(spec=spec, brief_document=brief, content_document=document)

    aligned_ids = [slide.id for slide in result.document.slides]
    assert aligned_ids == ["intro-slide", "solution-slide"]
    assert result.meta["applied"] == 2


def test_slide_id_aligner_skips_without_brief() -> None:
    spec = _build_spec()
    document = _build_content_document()
    aligner = SlideIdAligner()

    result = aligner.align(spec=spec, brief_document=None, content_document=document)

    assert result.document == document
    assert result.meta["status"] == "skipped"
