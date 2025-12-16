from __future__ import annotations

import json
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

import pptx_generator.cli as cli
from pptx_generator.cli import (
    DEFAULT_PREPARE_OUTPUT_DIR,
    PROMPT_TEMPLATE_DIRNAME,
    PROMPT_USER_SECTION_END,
    PROMPT_USER_SECTION_START,
    SLIDE_INPUTS_FILENAME,
    app,
)
from pptx_generator.cli_handlers.template_extraction import (
    TemplateExtractionResult,
    _ensure_slide_inputs_manifest,
    run_template_extraction,
)
from pptx_generator.cli_handlers.prepare import load_prompt_overrides
from pptx_generator.models import (
    JobSpecScaffold,
    JobSpecScaffoldMeta,
    JobSpecScaffoldBounds,
    JobSpecScaffoldPlaceholder,
    JobSpecScaffoldSlide,
    LayoutInfo,
    ShapeInfo,
    TemplateBlueprint,
    TemplateBlueprintSlide,
    TemplateBlueprintSlot,
    TemplateSpec,
)
from pptx_generator.prepare.source import PrepareSourceDocument
from pptx_generator.prepare_ai.client import MockPrepareLLMClient
from pptx_generator.prepare_ai.orchestrator import PrepareAIOrchestrator


def _build_static_template_spec() -> TemplateSpec:
    return TemplateSpec(
        template_path="templates/dummy.pptx",
        extracted_at="2025-01-01T00:00:00Z",
        template_source="slide",
        layouts=[
            LayoutInfo(
                name="TitleSlide",
                identifier="title_slide",
                anchors=[
                    ShapeInfo(
                        name="Title",
                        shape_type="TEXT",
                        left_in=1.0,
                        top_in=1.0,
                        width_in=4.0,
                        height_in=1.0,
                        text="",
                        placeholder_type="title",
                        is_placeholder=True,
                    )
                ],
            )
        ],
        warnings=[],
        errors=[],
        layout_mode="static",
        blueprint=TemplateBlueprint(
            slides=[
                TemplateBlueprintSlide(
                    slide_id="slide-01",
                    layout="TitleSlide",
                    required=True,
                    intent_tags=["overview"],
                    slots=[
                        TemplateBlueprintSlot(
                            slot_id="slide-01.title",
                            anchor="Title",
                            content_type="text",
                            required=True,
                            intent_tags=["headline"],
                        )
                    ],
                )
            ]
        ),
    )


def _build_jobspec_scaffold(template_spec_path: Path) -> JobSpecScaffold:
    return JobSpecScaffold(
        meta=JobSpecScaffoldMeta(
            schema_version="1.0",
            template_path="templates/dummy.pptx",
            template_id="tmpl",
            generated_at="2025-01-01T00:00:00Z",
            layout_count=1,
            layouts_path=None,
            template_spec_path=str(template_spec_path),
        ),
        slides=[
            JobSpecScaffoldSlide(
                id="slide-01",
                layout="TitleSlide",
                sequence=1,
                placeholders=[
                    JobSpecScaffoldPlaceholder(
                        anchor="Title",
                        kind="text",
                        placeholder_type="title",
                        shape_type="TEXT",
                        is_placeholder=True,
                        bounds=JobSpecScaffoldBounds(
                            left_in=1.0,
                            top_in=1.0,
                            width_in=4.0,
                            height_in=1.0,
                        ),
                        sample_text=None,
                        notes=[],
                        auto_draw=False,
                    )
                ],
            )
        ],
    )


def test_run_template_extraction_creates_prompt_files(monkeypatch, tmp_path) -> None:
    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"fake")

    base_dir = tmp_path / ".pptx"
    output_dir = base_dir / "template"
    output_dir.mkdir(parents=True, exist_ok=True)
    branding_path = output_dir / "branding.json"
    jobspec_path = output_dir / "jobspec.json"

    template_spec = _build_static_template_spec()

    class DummyExtractor:
        def __init__(self, options) -> None:  # noqa: ANN001
            self.options = options

        def extract(self) -> TemplateSpec:
            return template_spec

        def build_jobspec_scaffold(self, spec: TemplateSpec) -> JobSpecScaffold:
            return _build_jobspec_scaffold(template_spec_path=output_dir / "template_spec.json")

        def save_jobspec_scaffold(self, scaffold: JobSpecScaffold, path: Path) -> None:
            path.write_text("{}", encoding="utf-8")

    class DummyBranding:
        def to_branding_payload(self) -> dict[str, str]:
            return {"brand": "dummy"}

    monkeypatch.setattr(
        "pptx_generator.cli_handlers.template_extraction.TemplateExtractor",
        DummyExtractor,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_handlers.template_extraction.extract_branding_config",
        lambda _path: DummyBranding(),
    )

    monkeypatch.chdir(tmp_path)

    result = run_template_extraction(
        template_path=template_path,
        output_dir=output_dir,
        layout=None,
        anchor=None,
        output_format="json",
        template_ai_policy=None,
        template_ai_policy_id=None,
        disable_template_ai=True,
        layout_mode="static",
        static_source="slide",
        skip_validation=True,
        emit_slide_snapshot=False,
    )

    prompts_dir = output_dir / PROMPT_TEMPLATE_DIRNAME
    prompt_files = list(sorted(prompts_dir.glob("*.md")))
    assert prompt_files, "static モードでは雛形 Markdown が生成される"
    assert result.prompt_templates_created == len(prompt_files) == 1
    assert result.slide_inputs_path == base_dir / SLIDE_INPUTS_FILENAME
    assert result.slide_inputs_path.exists()


def test_load_prompt_overrides_reads_user_section(tmp_path) -> None:
    prompts_dir = tmp_path / PROMPT_TEMPLATE_DIRNAME
    prompts_dir.mkdir()
    sample = prompts_dir / "01_title.md"
    sample.write_text(
        "\n".join(
            [
                "header",
                PROMPT_USER_SECTION_START,
                "- 例: このスライドでは ROI の定量値を箇条書きで入れる",
                "- 章構成に沿って3点まとめる",
                PROMPT_USER_SECTION_END,
            ]
        ),
        encoding="utf-8",
    )

    template_spec = _build_static_template_spec()
    overrides = load_prompt_overrides(prompts_dir=prompts_dir, blueprint=template_spec.blueprint)

    assert overrides, "user-editable セクションを編集すると override が検出される"
    assert overrides[0].instructions == "- 章構成に沿って3点まとめる"


def test_cli_template_reports_prompt_directory(monkeypatch, tmp_path) -> None:
    template_file = tmp_path / "dummy.pptx"
    template_file.write_bytes(b"pptx")

    prompts_dir = tmp_path / "template" / PROMPT_TEMPLATE_DIRNAME
    prompts_dir.mkdir(parents=True)
    template_spec_path = tmp_path / "template" / "template_spec.json"
    template_spec_path.write_text("{}", encoding="utf-8")
    jobspec_path = tmp_path / "template" / "jobspec.json"
    jobspec_path.write_text("{}", encoding="utf-8")
    branding_path = tmp_path / "template" / "branding.json"
    branding_path.write_text("{}", encoding="utf-8")

    template_spec = _build_static_template_spec()
    layouts_path = tmp_path / "template" / "layouts.json"
    diagnostics_path = tmp_path / "template" / "diagnostics.json"
    layouts_path.write_text("{}", encoding="utf-8")
    diagnostics_path.write_text("{}", encoding="utf-8")
    layouts_path_value = layouts_path
    diagnostics_path_value = diagnostics_path

    class DummyValidationResult:  # noqa: D401 - simple stub
        errors_count = 0
        warnings_count = 0
        layouts_path = layouts_path_value
        diagnostics_path = diagnostics_path_value
        diff_report_path = None

    extraction_result = TemplateExtractionResult(
        template_spec=template_spec,
        jobspec_scaffold=_build_jobspec_scaffold(template_spec_path=template_spec_path),
        template_spec_path=template_spec_path,
        branding_path=branding_path,
        jobspec_path=jobspec_path,
        validation_result=DummyValidationResult(),
        output_dir=tmp_path / "template",
        slide_snapshot_path=None,
        prompt_templates_dir=prompts_dir,
        prompt_templates_created=2,
        slide_inputs_path=tmp_path / "slide_inputs.md",
    )

    def fake_extraction(**_kwargs):  # noqa: ANN002
        return extraction_result

    monkeypatch.setattr(
        "pptx_generator.cli_handlers.template_commands.run_template_extraction",
        fake_extraction,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_handlers.template_commands.run_template_release",
        lambda **_kwargs: None,
    )

    runner = CliRunner()
    result = runner.invoke(app, ["template", str(template_file), "--mode", "static"])

    assert result.exit_code == 0
    assert "プロンプト雛形を出力しました" in result.output
    assert "2 件のスライド雛形を生成しました" in result.output


def test_slot_contexts_do_not_duplicate_raw_context(tmp_path) -> None:
    source_path = Path("samples/input/pitch.md")
    source = PrepareSourceDocument.parse_file(source_path)
    template_spec = _build_static_template_spec()

    class CaptureClient(MockPrepareLLMClient):
        def __init__(self) -> None:  # noqa: D401
            super().__init__()
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, model_hint: str | None = None):  # noqa: ANN001, D401
            self.prompts.append(prompt)
            return super().generate(prompt, model_hint=model_hint)

    client = CaptureClient()
    orchestrator = PrepareAIOrchestrator(llm_client=client)

    slide_specific = PrepareSourceDocument(meta=source.meta, chapters=[], raw_text="- localized context")
    orchestrator.generate_document(
        source,
        mode="static",
        blueprint=template_spec.blueprint,
        blueprint_ref={"path": "template_spec.json", "hash": "deadbeef", "template_source": "slide"},
        prompt_overrides=[],
        slide_sources={"slide-01": slide_specific},
        slide_input_refs={"slide-01": "slide-input.txt"},
    )

    prompt_text = client.prompts[0]
    payload_text = prompt_text.split("# 入力", 1)[1]
    payload_text = payload_text.split("# 出力", 1)[0]
    json_part = payload_text[payload_text.index("{") : payload_text.rfind("}") + 1]
    payload = json.loads(json_part)

    raw_fragment = payload["raw_context"]["content"]
    slot_contexts = [slot.get("context", "") for slot in payload["slot_specs"]]

    assert raw_fragment.startswith("-")
    for context in slot_contexts:
        assert context == "- localized context"


def test_cli_prepare_uses_slide_inputs_manifest(monkeypatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")

    runner = CliRunner()
    with runner.isolated_filesystem():
        extract_dir = Path.cwd() / ".pptx/template"
        extract_dir.mkdir(parents=True, exist_ok=True)

        template_spec = _build_static_template_spec()
        template_spec_path = extract_dir / "template_spec.json"
        template_spec_path.write_text(template_spec.model_dump_json(indent=2), encoding="utf-8")

        jobspec = _build_jobspec_scaffold(template_spec_path=Path("template_spec.json"))
        jobspec_path = extract_dir / "jobspec.json"
        jobspec_path.write_text(json.dumps(jobspec.model_dump(mode="json"), indent=2), encoding="utf-8")

        sample_text = (Path(__file__).resolve().parents[2] / "samples/input/pitch.md").read_text(encoding="utf-8")
        sample_path = Path("samples/input/pitch.md")
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        sample_path.write_text(sample_text, encoding="utf-8")

        manifest_path = _ensure_slide_inputs_manifest(output_dir=extract_dir, template_spec=template_spec)
        assert manifest_path is not None
        manifest_path = manifest_path.resolve()
        expected_manifest_path = (template_spec_path.resolve().parent.parent / SLIDE_INPUTS_FILENAME)
        identifier = "01_titleslide"
        manifest_path.write_text(
            f"# Slide inputs\n{identifier}: samples/input/pitch.md\n",
            encoding="utf-8",
        )
        assert manifest_path.exists()
        assert expected_manifest_path == manifest_path

        cli.prepare.callback(
            prepare_inputs=(),
            output_dir=DEFAULT_PREPARE_OUTPUT_DIR,
            jobspec=jobspec_path,
            mode="static",
            page_limit=None,
        )

        prepare_dir = Path(".pptx/prepare")
        ai_log = json.loads((prepare_dir / "prepare_ai_log.json").read_text(encoding="utf-8"))
        assert ai_log[0]["slide_input_path"].endswith("pitch.md")

        meta = json.loads((prepare_dir / "ai_generation_meta.json").read_text(encoding="utf-8"))
        assert meta["slide_inputs"] == [
            {
                "slide_id": "slide-01",
                "input_path": str((Path.cwd() / sample_path).resolve()),
            }
        ]


def test_cli_prepare_requires_complete_manifest(monkeypatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")

    runner = CliRunner()
    with runner.isolated_filesystem():
        extract_dir = Path.cwd() / ".pptx/template"
        extract_dir.mkdir(parents=True, exist_ok=True)

        template_spec = _build_static_template_spec()
        template_spec_path = extract_dir / "template_spec.json"
        template_spec_path.write_text(template_spec.model_dump_json(indent=2), encoding="utf-8")
        jobspec = _build_jobspec_scaffold(template_spec_path=Path("template_spec.json"))
        jobspec_path = extract_dir / "jobspec.json"
        jobspec_path.write_text(json.dumps(jobspec.model_dump(mode="json"), indent=2), encoding="utf-8")

        manifest_path = _ensure_slide_inputs_manifest(output_dir=extract_dir, template_spec=template_spec)
        assert manifest_path is not None
        manifest_path.write_text("# empty manifest\n", encoding="utf-8")
        assert manifest_path.exists()

        with pytest.raises(click.exceptions.Exit) as excinfo:
            cli.prepare.callback(
                prepare_inputs=(),
                output_dir=DEFAULT_PREPARE_OUTPUT_DIR,
                jobspec=jobspec_path,
                mode="static",
                page_limit=None,
            )

        assert excinfo.value.exit_code == 2
