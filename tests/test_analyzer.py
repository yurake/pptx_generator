"""SimpleAnalyzerStep の診断結果を検証するテスト。"""

from __future__ import annotations

import json

from pptx_generator.models import FontSpec, JobAuth, JobMeta, JobSpec, Slide, SlideBullet, SlideImage
from pptx_generator.pipeline import AnalyzerOptions, PipelineContext, SimpleAnalyzerStep


def test_simple_analyzer_detects_quality_issues(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.0",
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
                    SlideBullet(
                        id="bullet-1",
                        text="本文",
                        level=4,
                        font=FontSpec(
                            name="Yu Gothic",
                            size_pt=12.0,
                            color_hex="#FFFFFF",
                        ),
                    )
                ],
                images=[
                    SlideImage(
                        id="img-1",
                        source="https://example.com/image.png",
                        left_in=0.1,
                        top_in=0.2,
                        width_in=9.5,
                        height_in=7.0,
                    )
                ],
            )
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
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
    assert {"margin", "font_min", "contrast_low", "bullet_depth", "layout_consistency"} <= issue_types

    fix_types = {fix["type"] for fix in payload["fixes"]}
    assert {"move", "font_raise", "color_adjust", "bullet_cap", "bullet_reindent"} <= fix_types

    # 余白補正の提案が具体値を伴うことを確認
    margin_issue = next(issue for issue in payload["issues"] if issue["type"] == "margin")
    assert margin_issue["fix"]["payload"]

    layout_issue = next(issue for issue in payload["issues"] if issue["type"] == "layout_consistency")
    assert layout_issue["fix"]["payload"]["level"] == 0
