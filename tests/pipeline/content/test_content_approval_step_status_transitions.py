"""承認コンテンツ読み込みステップのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptx_generator.models import (JobAuth, JobMeta, JobSpec, Slide,
                                   SlideBullet, SlideBulletGroup)
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.content_approval import (ContentApprovalError,
                                                      ContentApprovalOptions,
                                                      ContentApprovalStep)


def _create_job_spec() -> JobSpec:
    return JobSpec(
        meta=JobMeta(schema_version="1.0", title="テスト"),
        auth=JobAuth(created_by="tester"),
    )


def test_content_approval_step_loads_document_and_logs(tmp_path: Path) -> None:
    approved_path = tmp_path / "content_approved.json"
    review_log_path = tmp_path / "content_review_log.json"

    approved_payload = {
        "slides": [
            {
                "id": "s01",
                "intent": "市場動向",
                "status": "approved",
                "elements": {"title": "市場", "body": ["需要は増加"]},
                "applied_autofix": [],
            }
        ]
    }
    approved_path.write_text(json.dumps(approved_payload, ensure_ascii=False), encoding="utf-8")

    review_log_payload = [
        {
            "slide_id": "s01",
            "action": "approve",
            "actor": "editor@example.com",
            "timestamp": "2025-10-17T10:00:00+09:00",
        }
    ]
    review_log_path.write_text(json.dumps(review_log_payload, ensure_ascii=False), encoding="utf-8")

    context = PipelineContext(spec=_create_job_spec(), workdir=tmp_path)

    step = ContentApprovalStep(
        ContentApprovalOptions(
            approved_path=approved_path,
            review_log_path=review_log_path,
        )
    )

    step.run(context)

    assert "content_approved" in context.artifacts
    assert "content_approved_meta" in context.artifacts
    assert "content_review_log" in context.artifacts
    assert "content_review_log_meta" in context.artifacts
    document = context.artifacts["content_approved"]
    assert len(document.slides) == 1
    logs = context.artifacts["content_review_log"]
    assert len(logs) == 1
    doc_meta = context.artifacts["content_approved_meta"]
    assert doc_meta["slides"] == 1
    assert doc_meta["path"] == str(approved_path.resolve())
    assert doc_meta["hash"].startswith("sha256:")
    assert doc_meta["slide_ids"] == ["s01"]
    assert doc_meta["applied_to_spec"] is False
    assert doc_meta["updated_slide_ids"] == []
    log_meta = context.artifacts["content_review_log_meta"]
    assert log_meta["events"] == 1
    assert log_meta["path"] == str(review_log_path.resolve())
    assert log_meta["hash"].startswith("sha256:")
    assert log_meta["actions"] == {"approve": 1}


def test_content_approval_step_rejects_unapproved(tmp_path: Path) -> None:
    approved_path = tmp_path / "content_approved.json"
    approved_payload = {
        "slides": [
            {
                "id": "s01",
                "intent": "市場動向",
                "status": "draft",
                "elements": {"title": "市場", "body": ["需要は増加"]},
            }
        ]
    }
    approved_path.write_text(json.dumps(approved_payload, ensure_ascii=False), encoding="utf-8")

    context = PipelineContext(spec=_create_job_spec(), workdir=tmp_path)

    step = ContentApprovalStep(
        ContentApprovalOptions(
            approved_path=approved_path,
            require_all_approved=True,
        )
    )

    with pytest.raises(ContentApprovalError):
        step.run(context)


def test_content_approval_step_strips_comments(tmp_path: Path) -> None:
    approved_path = tmp_path / "content_approved.jsonc"
    approved_path.write_text(
        """
        {
          // コメント行
          "slides": [
            {
              "id": "s01",
              "intent": "市場動向",
              "status": "approved",
              "elements": {
                "title": "市場",
                "body": ["需要は増加"]
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    context = PipelineContext(spec=_create_job_spec(), workdir=tmp_path)
    step = ContentApprovalStep(
        ContentApprovalOptions(approved_path=approved_path)
    )

    step.run(context)
    document = context.artifacts["content_approved"]
    assert document.slides[0].id == "s01"


def test_content_approval_step_merges_into_spec(tmp_path: Path) -> None:
    approved_path = tmp_path / "content_approved.json"
    approved_payload = {
        "slides": [
            {
                "id": "agenda",
                "intent": "アジェンダ",
                "status": "approved",
                "elements": {
                    "title": "承認済みタイトル",
                    "body": ["Bullet 1", "Bullet 2"],
                    "note": "承認済みノート",
                },
            }
        ]
    }
    approved_path.write_text(json.dumps(approved_payload, ensure_ascii=False), encoding="utf-8")

    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="提案書"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="agenda",
                layout="Title",
                title="旧タイトル",
                bullets=[
                    SlideBulletGroup(
                        anchor=None,
                        items=[
                            SlideBullet(id="agenda-1", text="旧1", level=0),
                        ],
                    )
                ],
            )
        ],
    )

    context = PipelineContext(spec=spec, workdir=tmp_path)
    step = ContentApprovalStep(ContentApprovalOptions(approved_path=approved_path))
    step.run(context)

    slide = spec.slides[0]
    assert slide.title == "承認済みタイトル"
    assert [item.text for item in slide.bullets[0].items] == ["Bullet 1", "Bullet 2"]
    assert slide.notes == "承認済みノート"
