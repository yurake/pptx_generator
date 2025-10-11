"""SimpleRefinerStep の挙動を検証するテスト。"""

from __future__ import annotations

from pptx_generator.models import (
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
