"""AnalyzerReviewEngineAdapter のテスト。"""

from __future__ import annotations

from pptx_generator.models import (FontSpec, JobAuth, JobMeta, JobSpec, Slide,
                                   SlideBullet, SlideBulletGroup)
from pptx_generator.review_engine import AnalyzerReviewEngineAdapter


def _build_spec() -> JobSpec:
    return JobSpec(
        meta=JobMeta(schema_version="1.0", title="提案書"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                bullets=[
                    SlideBulletGroup(
                        anchor=None,
                        items=[
                            SlideBullet(
                                id="b1",
                                text="本文1",
                                level=2,
                                font=FontSpec(
                                    name="Test Font",
                                    size_pt=16.0,
                                    color_hex="#333333",
                                ),
                            )
                        ],
                    )
                ],
            )
        ],
    )


def test_build_payload_converts_issue_and_fix() -> None:
    spec = _build_spec()
    adapter = AnalyzerReviewEngineAdapter()

    analysis = {
        "issues": [
            {
                "id": "font_min-slide-1-b1-1",
                "type": "font_min",
                "severity": "warning",
                "message": "フォントサイズが不足しています",
                "target": {
                    "slide_id": "slide-1",
                    "element_id": "b1",
                    "element_type": "bullet",
                },
            }
        ],
        "fixes": [
            {
                "id": "fix-font_min-slide-1-b1-1",
                "issue_id": "font_min-slide-1-b1-1",
                "type": "font_raise",
                "target": {
                    "slide_id": "slide-1",
                    "element_id": "b1",
                    "element_type": "bullet",
                },
                "payload": {"size_pt": 20},
            },
            {
                "id": "fix-grid-slide-1-b1",
                "issue_id": "grid-slide-1-b1",
                "type": "move",
                "target": {
                    "slide_id": "slide-1",
                    "element_id": "b1",
                    "element_type": "bullet",
                },
                "payload": {"left_in": 1.25},
            },
        ],
    }

    payload = adapter.build_payload(analysis, spec)

    assert payload["schema_version"] == "1.0.0"
    assert payload["slides"]

    slide_payload = payload["slides"][0]
    assert slide_payload["slide_id"] == "slide-1"
    assert slide_payload["grade"] == "B"
    assert slide_payload["issues"][0]["code"] == "font_min"

    autofix = slide_payload["autofix_proposals"][0]
    patch = autofix["patch"][0]
    assert patch["op"] == "replace"
    assert patch["path"].endswith("/font/size_pt")
    assert patch["value"] == 20.0

    assert "notes" in slide_payload
    assert "move" in slide_payload["notes"]["unsupported_fix_types"]
