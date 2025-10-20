from pptx_generator.models import Slide, SlideBullet, SlideBulletGroup
from pptx_generator.pipeline.render_audit import RenderingAuditStep


def test_expects_body_with_anchored_bullet_group() -> None:
    slide = Slide(
        id="slide-1",
        layout="layout",
        bullets=[
            SlideBulletGroup(
                anchor="shape_1",
                items=[SlideBullet(id="bullet-1", text="foo")],
            )
        ],
    )

    assert RenderingAuditStep._expects_body(slide) is True
