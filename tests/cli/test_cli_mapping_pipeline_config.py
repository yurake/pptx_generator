from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast

import pptx_generator.cli_handlers.mapping as mapping
from pptx_generator.models import (GenerateReadyDocument, GenerateReadyMeta,
                                   TemplateStyle)
from pptx_generator.pipeline import PipelineContext
from pptx_generator.pipeline.refiner import RefinerOptions
from pptx_generator.settings import RulesConfig


def _make_params(tmp_path) -> mapping.MappingPipelineConfig:
    style_payload = mapping.TemplateStylePayload(
        style=TemplateStyle.default(),
        artifact={"source": "test-template"},
    )
    return mapping.MappingPipelineConfig(
        spec=cast(object, SimpleNamespace(slides=[], meta=None)),
        output_dir=tmp_path / "out",
        spec_source_path=tmp_path / "spec.json",
        rules_config=RulesConfig(),
        refiner_options=RefinerOptions(),
        template_style=style_payload,
        prepare_cards=None,
        require_prepare=True,
        layouts=tmp_path / "layouts.jsonl",
        draft_output=tmp_path / "draft",
        template=tmp_path / "template.pptx",
    )


def test_run_mapping_pipeline_builds_context_from_config(monkeypatch, tmp_path):
    params = _make_params(tmp_path)

    captured: dict[str, object] = {}

    def fake_run_draft_pipeline(**kwargs):
        captured["draft_kwargs"] = kwargs
        meta_src = tmp_path / "draft" / "generate_ready_meta.json"
        meta_src.parent.mkdir(parents=True, exist_ok=True)
        meta_src.write_text("{}", encoding="utf-8")
        return PipelineContext(
            spec=kwargs["spec"],
            workdir=kwargs["output_dir"],
            artifacts={"generate_ready_meta_path": str(meta_src)},
        )

    monkeypatch.setattr(mapping, "run_draft_pipeline", fake_run_draft_pipeline)

    def fake_spec_validator(**kwargs):
        captured["validator_kwargs"] = kwargs
        return SimpleNamespace(name="validator")

    def fake_refiner(options):
        captured["refiner_options"] = options
        return SimpleNamespace(name="refiner")

    def fake_mapping(options):
        captured["mapping_options"] = options
        return SimpleNamespace(name="mapping")

    class DummyRunner:
        def __init__(self, steps):
            captured["steps"] = steps

        def execute(self, context: PipelineContext) -> None:
            context.add_artifact("runner_executed", True)

    monkeypatch.setattr(mapping, "SpecValidatorStep", fake_spec_validator)
    monkeypatch.setattr(mapping, "SimpleRefinerStep", fake_refiner)
    monkeypatch.setattr(mapping, "MappingStep", fake_mapping)
    monkeypatch.setattr(mapping, "PipelineRunner", DummyRunner)

    result = mapping.run_mapping_pipeline(
        params=params,
        generate_ready_filename="generate_ready.json",
        generate_ready_meta_filename="generate_ready_meta.json",
    )

    assert result.workdir == params.output_dir
    assert result.artifacts["template_style"] == params.template_style.artifact
    assert result.artifacts["template_style_data"] == params.template_style.style
    assert result.artifacts["runner_executed"] is True

    copied_meta = params.output_dir / "generate_ready_meta.json"
    assert copied_meta.exists()

    assert captured["draft_kwargs"]["require_prepare"] is True
    assert captured["refiner_options"] == params.refiner_options
    mapping_options = captured["mapping_options"]
    assert mapping_options.template_path == params.template


def test_run_mapping_pipeline_static_pass_through(monkeypatch, tmp_path):
    params = _make_params(tmp_path)

    def fail_run_draft_pipeline(**_):  # pragma: no cover - safety guard
        raise AssertionError("draft pipeline must not be invoked")

    class FailRunner:  # pragma: no cover - safety guard
        def __init__(self, _steps):
            raise AssertionError("pipeline runner should not run for static output")

    monkeypatch.setattr(mapping, "run_draft_pipeline", fail_run_draft_pipeline)
    monkeypatch.setattr(mapping, "PipelineRunner", FailRunner)

    meta_src = tmp_path / "draft" / "generate_ready_meta.json"
    meta_src.parent.mkdir(parents=True, exist_ok=True)
    meta_src.write_text(json.dumps({"mode": "static"}), encoding="utf-8")

    generate_ready = GenerateReadyDocument(
        slides=[],
        meta=GenerateReadyMeta(
            generated_at="2025-01-01T00:00:00Z",
            layout_mode="static",
        ),
    )

    draft_context = PipelineContext(
        spec=params.spec,
        workdir=params.draft_output,
        artifacts={
            "generate_ready": generate_ready,
            "generate_ready_meta_path": str(meta_src),
        },
    )

    result = mapping.run_mapping_pipeline(
        params=params,
        draft_context=draft_context,
        generate_ready_filename="generate_ready.json",
        generate_ready_meta_filename="generate_ready_meta.json",
    )

    ready_artifact = result.artifacts["generate_ready"]
    assert ready_artifact.meta.template_path == str(params.template)

    ready_path = params.output_dir / "generate_ready.json"
    assert ready_path.exists()

    meta_path = params.output_dir / "generate_ready_meta.json"
    assert meta_path.exists()
