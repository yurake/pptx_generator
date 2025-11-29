from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import (
    DEFAULT_PREPARE_POLICY_PATH,
    PROMPT_TEMPLATE_DIRNAME,
    PROMPT_USER_SECTION_END,
    PROMPT_USER_SECTION_START,
    TemplateExtractionResult,
    _ensure_prompt_templates,
    _load_prompt_overrides,
    _run_template_extraction,
    app,
)
from pptx_generator.models import (
    JobSpecScaffold,
    JobSpecScaffoldMeta,
    TemplateBlueprint,
    TemplateBlueprintSlide,
    TemplateBlueprintSlot,
    TemplateSpec,
)
from pptx_generator.prepare.policy import load_prepare_policy_set
from pptx_generator.prepare.source import PrepareSourceDocument
from pptx_generator.prepare_ai.llm_client import MockPrepareLLMClient
from pptx_generator.prepare_ai.orchestrator import PrepareAIOrchestrator


def _build_static_template_spec() -> TemplateSpec:
    return TemplateSpec(
        template_path="templates/dummy.pptx",
        extracted_at="2025-01-01T00:00:00Z",
        layouts=[],
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
        slides=[],
    )


def test_run_template_extraction_creates_prompt_files(monkeypatch, tmp_path) -> None:
    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"fake")

    output_dir = tmp_path / "extract"
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

    monkeypatch.setattr("pptx_generator.cli.TemplateExtractor", DummyExtractor)
    monkeypatch.setattr("pptx_generator.cli.extract_branding_config", lambda _path: DummyBranding())

    result = _run_template_extraction(
        template_path=template_path,
        output_dir=output_dir,
        layout=None,
        anchor=None,
        output_format="json",
        template_ai_policy=None,
        template_ai_policy_id=None,
        disable_template_ai=True,
        layout_mode="static",
        skip_validation=True,
        emit_slide_snapshot=False,
    )

    prompts_dir = output_dir / PROMPT_TEMPLATE_DIRNAME
    prompt_files = list(sorted(prompts_dir.glob("*.md")))
    assert prompt_files, "static モードでは雛形 Markdown が生成される"
    assert result.prompt_templates_created == len(prompt_files) == 1


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
    overrides = _load_prompt_overrides(prompts_dir=prompts_dir, blueprint=template_spec.blueprint)

    assert overrides, "user-editable セクションを編集すると override が検出される"
    assert overrides[0].instructions == "- 章構成に沿って3点まとめる"


def test_cli_template_reports_prompt_directory(monkeypatch, tmp_path) -> None:
    template_file = tmp_path / "dummy.pptx"
    template_file.write_bytes(b"pptx")

    prompts_dir = tmp_path / "extract" / PROMPT_TEMPLATE_DIRNAME
    prompts_dir.mkdir(parents=True)
    template_spec_path = tmp_path / "extract" / "template_spec.json"
    template_spec_path.write_text("{}", encoding="utf-8")
    jobspec_path = tmp_path / "extract" / "jobspec.json"
    jobspec_path.write_text("{}", encoding="utf-8")
    branding_path = tmp_path / "extract" / "branding.json"
    branding_path.write_text("{}", encoding="utf-8")

    template_spec = _build_static_template_spec()
    layouts_path = tmp_path / "extract" / "layouts.json"
    diagnostics_path = tmp_path / "extract" / "diagnostics.json"
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
        output_dir=tmp_path / "extract",
        slide_snapshot_path=None,
        prompt_templates_dir=prompts_dir,
        prompt_templates_created=2,
    )

    def fake_extraction(**_kwargs):  # noqa: ANN002
        return extraction_result

    monkeypatch.setattr("pptx_generator.cli._run_template_extraction", fake_extraction)
    monkeypatch.setattr("pptx_generator.cli._run_template_release", lambda **_kwargs: None)

    runner = CliRunner()
    result = runner.invoke(app, ["template", str(template_file), "--layout-mode", "static"])

    assert result.exit_code == 0
    assert "プロンプト雛形を出力しました" in result.output
    assert "2 件のスライド雛形を生成しました" in result.output


def test_slot_contexts_do_not_duplicate_raw_context(tmp_path) -> None:
    source_path = Path("samples/contents/sample_import_content.txt")
    source = PrepareSourceDocument.parse_file(source_path)
    policy_set = load_prepare_policy_set(Path(DEFAULT_PREPARE_POLICY_PATH))
    template_spec = _build_static_template_spec()

    class CaptureClient(MockPrepareLLMClient):
        def __init__(self) -> None:  # noqa: D401
            super().__init__()
            self.prompts: list[str] = []

        def generate(self, prompt: str, *, model_hint: str | None = None):  # noqa: ANN001, D401
            self.prompts.append(prompt)
            return super().generate(prompt, model_hint=model_hint)

    client = CaptureClient()
    orchestrator = PrepareAIOrchestrator(policy_set, llm_client=client)

    orchestrator.generate_document(
        source,
        mode="static",
        blueprint=template_spec.blueprint,
        blueprint_ref={"path": "template_spec.json", "hash": "deadbeef"},
        prompt_overrides=[],
    )

    prompt_text = client.prompts[0]
    payload_text = prompt_text.split("# 入力", 1)[1]
    payload_text = payload_text.split("# 出力", 1)[0]
    json_part = payload_text[payload_text.index("{") : payload_text.rfind("}") + 1]
    payload = json.loads(json_part)

    raw_fragment = payload["raw_context"]["content"]
    slot_contexts = [slot.get("context", "") for slot in payload["slot_specs"]]

    assert raw_fragment.startswith("-")  # sanity check
    for context in slot_contexts:
        assert "ブランド統一" not in context
        assert context != raw_fragment
