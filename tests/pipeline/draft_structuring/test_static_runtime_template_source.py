from __future__ import annotations

import datetime

import pytest

from pptx_generator.models import TemplateBlueprint, TemplateBlueprintSlide, TemplateSpec
from pptx_generator.pipeline.draft_structuring.static_runtime import (
    DraftStructuringError,
    validate_static_template_spec,
)
from pptx_generator.prepare.models import PrepareGenerationMeta


class DummyStep:
    def _compute_blueprint_hash(self, blueprint) -> str:  # noqa: ANN001
        return "deadbeef"


def test_validate_static_template_spec_template_source_mismatch() -> None:
    template_spec = TemplateSpec(
        template_path="templates/sample.pptx",
        extracted_at="2025-12-07T00:00:00Z",
        layout_mode="static",
        template_source="slide",
        blueprint=TemplateBlueprint(
            slides=[
                TemplateBlueprintSlide(
                    slide_id="slide-1",
                    layout="Title",
                    required=True,
                    slots=[],
                )
            ]
        ),
    )
    prepare_meta = PrepareGenerationMeta(
        prepare_id="prepare-1",
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        input_hash="hash",
        statistics={},
        cards=[],
        mode="static",
        template_source="template",
    )

    with pytest.raises(DraftStructuringError, match="template_source"):
        validate_static_template_spec(DummyStep(), template_spec, prepare_meta)
