from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from click.testing import CliRunner

from pptx_generator.cli import app
from pptx_generator.cli_handlers.prepare import (
    PrepareCommandArtifacts,
    PrepareCommandError,
    PrepareCommandResult,
    PrepareStaticContext,
    _load_prepare_inputs,
    _load_prepare_input,
    resolve_static_context,
)
from pptx_generator.cli_hooks import STAGE_PREPARE
from pptx_generator.models import TemplateBlueprint, TemplateBlueprintSlide, TemplateBlueprintSlot, TemplateSpec
from pptx_generator.prepare_ai.client import MockPrepareLLMClient, PrepareLLMResult
from pptx_generator.prepare_ai.orchestrator import PrepareAIOrchestrator, StaticPromptOverride
from pptx_generator.prepare.policy import load_prepare_policy_set
from pptx_generator.prepare.source import PrepareSourceDocument, PrepareSourceMeta
from pptx_generator.prepare.models import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareNoteEntry,
    PrepareAIRecord,
    PrepareDocument,
    PrepareGenerationMeta,
)
from pptx_generator.pipeline.draft_structuring import DraftStructuringStep


SAMPLE_PREPARE_SOURCE = Path("samples/input/pitch.md")


def test_resolve_static_context_dynamic_mode(tmp_path: Path) -> None:
    context = resolve_static_context(
        jobspec_path=None,
        default_jobspec_path=tmp_path / "jobspec.json",
        prompts_dirname=Path("prompts"),
        slide_inputs_filename=Path("slide_inputs.md"),
        mode="dynamic",
        prepare_path=None,
        has_inline_source=False,
    )

    assert context.blueprint_spec is None
    assert context.prompt_overrides == []
    assert context.messages == []


def test_resolve_static_context_requires_jobspec(tmp_path: Path) -> None:
    with pytest.raises(PrepareCommandError):
        resolve_static_context(
            jobspec_path=None,
            default_jobspec_path=tmp_path / "missing_jobspec.json",
            prompts_dirname=Path("prompts"),
            slide_inputs_filename=Path("slide_inputs.md"),
            mode="static",
            prepare_path=None,
            has_inline_source=False,
        )


def test_prepare_command_artifacts_write_outputs(tmp_path: Path) -> None:
    artifacts = PrepareCommandArtifacts.initialize(tmp_path / "prepare")
    document = PrepareDocument(prepare_id="prep-1")
    meta = PrepareGenerationMeta(
        prepare_id="prep-1",
        policy_id="policy",
        input_hash="hash",
        cards=[],
    )
    ai_logs = [PrepareAIRecord(card_id="card-1", prompt_template="template.md")]
    context = PrepareStaticContext(
        blueprint_spec=None,
        blueprint_ref=None,
        template_spec_path=None,
        prompt_overrides=[],
        slide_input_sources=None,
        slide_input_refs=None,
        source_document=None,
        messages=["applied"],
        import_metadata=[],
    )

    result = artifacts.write_outputs(
        document=document,
        meta=meta,
        ai_logs=ai_logs,
        dump_json=lambda path, payload: path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        ),
        static_context=context,
        messages=context.messages,
        import_metadata=context.import_metadata,
    )

    assert result.cards_path.exists()
    assert result.audit_path.exists()
    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["prepare_normalization"]["statistics"] == meta.statistics


def test_resolve_static_context_imports_slide_inputs(monkeypatch, tmp_path: Path) -> None:
    template_dir = tmp_path / "extract"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_spec_path = template_dir / "template_spec.json"
    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="slide-01",
                layout="StaticLayout",
                required=True,
                intent_tags=["overview"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="slot-title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        intent_tags=["headline"],
                    )
                ],
            )
        ]
    )
    template_spec_path.write_text(
        json.dumps(
            TemplateSpec(
                template_path="templates/sample.pptx",
                extracted_at="2025-12-04T00:00:00Z",
                layouts=[],
                layout_mode="static",
                blueprint=blueprint,
            ).model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    jobspec_path = tmp_path / "jobspec.json"
    jobspec_path.write_text(
        json.dumps(
            {
                "meta": {
                    "schema_version": "2025-01-01",
                    "title": "Static Prepare",
                    "template_path": "templates/sample.pptx",
                    "template_spec_path": "extract/template_spec.json",
                },
                "auth": {"created_by": "tester"},
                "slides": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    slide_manifest = tmp_path / "slide_inputs.md"
    slide_manifest.write_text("01_staticlayout: dummy.pdf\n", encoding="utf-8")

    dummy_document = PrepareSourceDocument(
        meta=PrepareSourceMeta(title="Imported", prepare_id=None),
        chapters=[],
        raw_text="dummy",
    )

    def fake_load_prepare_input(value: str, service: object) -> tuple[PrepareSourceDocument, list[dict[str, object]], list[str]]:
        return dummy_document, [{"source": value, "via": "content_import"}], [f"インポートを完了しました: {value}"]

    monkeypatch.setattr("pptx_generator.cli_handlers.prepare._load_prepare_input", fake_load_prepare_input)

    context = resolve_static_context(
        jobspec_path=jobspec_path,
        default_jobspec_path=jobspec_path,
        prompts_dirname=Path("prompts"),
        slide_inputs_filename=Path("slide_inputs.md"),
        mode="static",
        prepare_path=None,
        has_inline_source=False,
    )

    assert context.slide_input_sources is not None
    assert "slide-01" in context.slide_input_sources
    assert context.import_metadata
    assert context.import_metadata[0]["via"] == "content_import"
    assert str(context.import_metadata[0]["source"]).endswith("dummy.pdf")
    assert dummy_document is context.source_document
    assert any("インポートを完了しました" in message for message in context.messages)


def test_resolve_static_context_placeholder_manifest_allows_cli_inputs(tmp_path: Path) -> None:
    template_dir = tmp_path / "extract"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_spec_path = template_dir / "template_spec.json"
    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="slide-01",
                layout="StaticLayout",
                required=True,
                intent_tags=["overview"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="slot-title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        intent_tags=["headline"],
                    )
                ],
            )
        ]
    )
    template_spec_path.write_text(
        json.dumps(
            TemplateSpec(
                template_path="templates/sample.pptx",
                extracted_at="2025-12-04T00:00:00Z",
                layouts=[],
                layout_mode="static",
                blueprint=blueprint,
            ).model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    jobspec_path = tmp_path / "jobspec.json"
    jobspec_path.write_text(
        json.dumps(
            {
                "meta": {
                    "schema_version": "2025-01-01",
                    "title": "Static Prepare",
                    "template_path": "templates/sample.pptx",
                    "template_spec_path": "extract/template_spec.json",
                },
                "auth": {"created_by": "tester"},
                "slides": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    slide_manifest = tmp_path / "slide_inputs.md"
    slide_manifest.write_text("01_staticlayout: <TODO>\n", encoding="utf-8")

    context = resolve_static_context(
        jobspec_path=jobspec_path,
        default_jobspec_path=jobspec_path,
        prompts_dirname=Path("prompts"),
        slide_inputs_filename=Path("slide_inputs.md"),
        mode="static",
        prepare_path=None,
        has_inline_source=True,
    )

    assert context.slide_input_sources is None
    assert any("プレースホルダーのみ" in message for message in context.messages)


def test_resolve_static_context_placeholder_manifest_requires_inputs(tmp_path: Path) -> None:
    template_dir = tmp_path / "extract"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_spec_path = template_dir / "template_spec.json"
    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="slide-01",
                layout="StaticLayout",
                required=True,
                intent_tags=["overview"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="slot-title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        intent_tags=["headline"],
                    )
                ],
            )
        ]
    )
    template_spec_path.write_text(
        json.dumps(
            TemplateSpec(
                template_path="templates/sample.pptx",
                extracted_at="2025-12-04T00:00:00Z",
                layouts=[],
                layout_mode="static",
                blueprint=blueprint,
            ).model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    jobspec_path = tmp_path / "jobspec.json"
    jobspec_path.write_text(
        json.dumps(
            {
                "meta": {
                    "schema_version": "2025-01-01",
                    "title": "Static Prepare",
                    "template_path": "templates/sample.pptx",
                    "template_spec_path": "extract/template_spec.json",
                },
                "auth": {"created_by": "tester"},
                "slides": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    slide_manifest = tmp_path / "slide_inputs.md"
    slide_manifest.write_text("01_staticlayout: <TODO>\n", encoding="utf-8")

    with pytest.raises(PrepareCommandError) as exc_info:
        resolve_static_context(
            jobspec_path=jobspec_path,
            default_jobspec_path=jobspec_path,
            prompts_dirname=Path("prompts"),
            slide_inputs_filename=Path("slide_inputs.md"),
            mode="static",
            prepare_path=None,
            has_inline_source=False,
        )

    assert "slide_inputs.md に有効な入力が含まれていません" in str(exc_info.value)


def test_prepare_generates_outputs(tmp_path) -> None:
    output_dir = tmp_path / "prepare"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "prepare",
            str(SAMPLE_PREPARE_SOURCE),
            "--mode",
            "dynamic",
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    prepare_dir = output_dir
    cards_path = prepare_dir / "prepare_card.json"
    log_path = prepare_dir / "prepare_log.json"
    ai_log_path = prepare_dir / "prepare_ai_log.json"
    meta_path = prepare_dir / "ai_generation_meta.json"
    outline_path = prepare_dir / "prepare_story_outline.json"
    audit_path = prepare_dir / "audit_log.json"

    for path in [cards_path, log_path, ai_log_path, meta_path, outline_path, audit_path]:
        assert path.exists(), f"{path} が生成されていること"

    cards_payload = json.loads(cards_path.read_text(encoding="utf-8"))
    assert cards_payload["prepare_id"]
    card_count = len(cards_payload["cards"])
    assert card_count >= 1
    first_card = cards_payload["cards"][0]
    assert first_card["role"]["story_phase"] in {"introduction", "problem", "solution", "impact", "next"}
    assert first_card["content"]["title"]
    assert first_card["content"].get("headline") is None
    assert isinstance(first_card["content"].get("body", []), list)

    log_payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert log_payload == []

    ai_log_payload = json.loads(ai_log_path.read_text(encoding="utf-8"))
    assert len(ai_log_payload) == card_count
    for entry in ai_log_payload:
        assert entry["card_id"]
        assert "llm_stub" not in entry.get("warnings", [])

    meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta_payload["mode"] == "dynamic"
    assert meta_payload["statistics"]["cards_total"] == card_count
    assert meta_payload.get("constraints", {}).get("include_title_page") is True
    assert meta_payload["import_sources"]
    assert meta_payload["import_sources"][0]["via"] in {"structured", "content_import"}

    outline_payload = json.loads(outline_path.read_text(encoding="utf-8"))
    assert outline_payload["chapters"]
    assert outline_payload["chapters"][0]["id"]

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    prepare_meta = audit_payload["prepare_normalization"]
    assert prepare_meta["policy_id"]
    assert prepare_meta["statistics"]["cards_total"] == card_count
    assert prepare_meta["mode"] == "dynamic"
    outputs = prepare_meta["outputs"]
    assert outputs["prepare_card"].endswith("prepare_card.json")
    assert prepare_meta.get("import_sources")


def test_prepare_requires_valid_prepare_source(tmp_path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["prepare", str(invalid_path), "--mode", "dynamic"],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "解析に失敗" in result.output


def test_prepare_respects_page_limit(tmp_path) -> None:
    output_dir = tmp_path / "limited"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "prepare",
            str(SAMPLE_PREPARE_SOURCE),
            "--mode",
            "dynamic",
            "--output",
            str(output_dir),
            "--page-limit",
            "2",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    cards_payload = json.loads((output_dir / "prepare_card.json").read_text(encoding="utf-8"))
    card_count = len(cards_payload["cards"])
    assert card_count >= 1
    first_card = cards_payload["cards"][0]
    assert first_card["content"].get("title") is None
    assert first_card["content"].get("headline")
    ai_log_payload = json.loads((output_dir / "prepare_ai_log.json").read_text(encoding="utf-8"))
    assert len(ai_log_payload) == card_count
    meta_payload = json.loads((output_dir / "ai_generation_meta.json").read_text(encoding="utf-8"))
    assert meta_payload["statistics"]["cards_total"] == card_count
    assert meta_payload.get("constraints", {}).get("max_chapters") == 2

def test_prepare_page_limit_short_option(tmp_path) -> None:
    output_dir = tmp_path / "short"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "prepare",
            str(SAMPLE_PREPARE_SOURCE),
            "--mode",
            "dynamic",
            "--output",
            str(output_dir),
            "-p",
            "1",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    cards_payload = json.loads((output_dir / "prepare_card.json").read_text(encoding="utf-8"))
    card_count = len(cards_payload["cards"])
    assert card_count >= 1
    ai_log_payload = json.loads((output_dir / "prepare_ai_log.json").read_text(encoding="utf-8"))
    assert len(ai_log_payload) == card_count
    meta_payload = json.loads((output_dir / "ai_generation_meta.json").read_text(encoding="utf-8"))
    assert meta_payload.get("constraints", {}).get("max_chapters") == 1


def test_prepare_accepts_multiple_inputs(tmp_path) -> None:
    source_a = tmp_path / "source_a.md"
    source_a.write_text("# イントロ\n- 課題A\n\n## 詳細\n- 詳細A1", encoding="utf-8")
    source_b = tmp_path / "source_b.md"
    source_b.write_text("# 提案\n- 提案A\n- 提案B", encoding="utf-8")
    output_di...