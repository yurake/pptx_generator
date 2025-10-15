"""SimpleRefinerStep の挙動を検証するテスト。"""

from __future__ import annotations

import pytest

from pptx_generator.models import (
    FontSpec,
    JobAuth,
    JobMeta,
    JobSpec,
    Slide,
    SlideBullet,
    SlideBulletGroup,
)
from pptx_generator.pipeline import PipelineContext, RefinerOptions, SimpleRefinerStep

def _group(*bullets: SlideBullet, anchor: str | None = None) -> SlideBulletGroup:
    return SlideBulletGroup(anchor=anchor, items=list(bullets))


def test_refiner_reindents_nested_bullets(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="Refiner テスト",
            client="Test",
            author="営業部",
            created_at="2025-10-07",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                bullets=[
                    _group(
                        SlideBullet(id="bullet-1", text="親", level=0),
                        SlideBullet(id="bullet-2", text="飛び級", level=3),
                        SlideBullet(id="bullet-3", text="更に飛び級", level=4),
                        SlideBullet(id="bullet-4", text="正常", level=2),
                    )
                ],
            )
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    refiner = SimpleRefinerStep(RefinerOptions(max_bullet_level=3))

    refiner.run(context)

    levels = [bullet.level for bullet in context.spec.slides[0].iter_bullets()]
    assert levels == [0, 1, 2, 2]

    adjustments = context.require_artifact("refiner_adjustments")
    assert adjustments == [
        {
            "slide_id": "slide-1",
            "element_id": "bullet-2",
            "type": "bullet_reindent",
            "from_level": 3,
            "to_level": 1,
        },
        {
            "slide_id": "slide-1",
            "element_id": "bullet-3",
            "type": "bullet_reindent",
            "from_level": 4,
            "to_level": 2,
        },
    ]


def test_refiner_skips_when_disabled(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="Refiner 無効化テスト",
            client="Test",
            author="営業部",
            created_at="2025-10-07",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                bullets=[
                    _group(
                        SlideBullet(id="bullet-1", text="親", level=0),
                        SlideBullet(id="bullet-2", text="飛び級", level=3),
                    )
                ],
            )
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    refiner = SimpleRefinerStep(RefinerOptions(enable_bullet_reindent=False))

    refiner.run(context)

    levels = [bullet.level for bullet in context.spec.slides[0].iter_bullets()]
    assert levels == [0, 3]

    adjustments = context.require_artifact("refiner_adjustments")
    assert adjustments == []


def test_refiner_raises_font_size(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="Font Raise テスト",
            client="Test",
            author="営業部",
            created_at="2025-10-07",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                bullets=[
                    _group(
                        SlideBullet(
                            id="bullet-1",
                            text="本文",
                            level=0,
                            font=FontSpec(name="Yu Gothic", size_pt=12.0, color_hex="#111111"),
                        )
                    )
                ],
            )
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    refiner = SimpleRefinerStep(
        RefinerOptions(
            max_bullet_level=3,
            enable_bullet_reindent=False,
            enable_font_raise=True,
            min_font_size=18.0,
            enable_color_adjust=False,
            default_font_name="Yu Gothic",
        )
    )

    refiner.run(context)

    bullet = next(context.spec.slides[0].iter_bullets())
    assert bullet.font is not None
    assert bullet.font.size_pt == pytest.approx(18.0)

    adjustments = context.require_artifact("refiner_adjustments")
    assert any(adj["type"] == "font_raise" for adj in adjustments)


def test_refiner_adjusts_font_color(tmp_path) -> None:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="Color Adjust テスト",
            client="Test",
            author="営業部",
            created_at="2025-10-07",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                bullets=[
                    _group(
                        SlideBullet(
                            id="bullet-1",
                            text="本文",
                            level=0,
                            font=FontSpec(name="Yu Gothic", size_pt=18.0, color_hex="#FF0000"),
                        )
                    ),
                    _group(
                        SlideBullet(
                            id="bullet-2",
                            text="フォント未指定",
                            level=0,
                        )
                    ),
                ],
            )
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    target_color = "#005BAC"
    refiner = SimpleRefinerStep(
        RefinerOptions(
            max_bullet_level=3,
            enable_bullet_reindent=False,
            enable_font_raise=False,
            enable_color_adjust=True,
            preferred_text_color=target_color,
            fallback_font_color="#333333",
            default_font_name="Yu Gothic",
        )
    )

    refiner.run(context)

    bullets = list(context.spec.slides[0].iter_bullets())
    assert bullets[0].font is not None
    assert bullets[0].font.color_hex == target_color
    assert bullets[1].font is not None
    assert bullets[1].font.color_hex == target_color

    adjustments = context.require_artifact("refiner_adjustments")
    color_adjustments = [adj for adj in adjustments if adj["type"] == "color_adjust"]
    assert len(color_adjustments) >= 2
