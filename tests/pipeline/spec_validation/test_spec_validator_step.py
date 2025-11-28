"""SpecValidatorStep の検証テスト。"""

from __future__ import annotations

import pytest

from pathlib import Path

from pptx_generator.models import (
    JobAuth,
    JobMeta,
    JobSpec,
    Slide,
    SlideBullet,
    SlideBulletGroup,
)
from pptx_generator.models import SpecValidationError
from pptx_generator.pipeline import PipelineContext, SpecValidatorStep

def _group(*bullets: SlideBullet, anchor: str | None = None) -> SlideBulletGroup:
    return SlideBulletGroup(anchor=anchor, items=list(bullets))


def _build_spec(*, title: str = "タイトル", bullet_text: str = "本文", level: int = 0) -> JobSpec:
    slide = Slide(
        id="slide-1",
        layout="Title and Content",
        title=title,
        bullets=[
            _group(
                SlideBullet(id="bullet-1", text=bullet_text, level=level),
            )
        ],
    )
    return JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="Proposal",
            client="client",
            author="author",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[slide],
    )


def _build_context(spec: JobSpec) -> PipelineContext:
    return PipelineContext(spec=spec, workdir=Path("."))


@pytest.fixture
def validator() -> SpecValidatorStep:
    return SpecValidatorStep(
        max_title_length=10,
        max_bullet_length=10,
        max_bullet_level=2,
        forbidden_words=("禁止",),
    )


def test_validator_passes_when_conditions_met(validator: SpecValidatorStep) -> None:
    spec = _build_spec(title="タイトル", bullet_text="本文", level=1)
    context = _build_context(spec)
    validator.run(context)


def test_validator_rejects_long_title(validator: SpecValidatorStep) -> None:
    spec = _build_spec(title="これは明らかに長すぎるタイトルです")
    context = _build_context(spec)
    with pytest.raises(SpecValidationError):
        validator.run(context)


def test_validator_rejects_forbidden_word(validator: SpecValidatorStep) -> None:
    spec = _build_spec(bullet_text="禁止ワードを含む")
    context = _build_context(spec)
    with pytest.raises(SpecValidationError):
        validator.run(context)


def test_validator_rejects_bullet_level(validator: SpecValidatorStep) -> None:
    spec = _build_spec(level=3)
    context = _build_context(spec)
    with pytest.raises(SpecValidationError):
        validator.run(context)
