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
    output_dir = tmp_path / "multi"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "prepare",
            str(source_a),
            str(source_b),
            "--mode",
            "dynamic",
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    meta_payload = json.loads((output_dir / "ai_generation_meta.json").read_text(encoding="utf-8"))
    import_sources = meta_payload.get("import_sources", [])
    assert len(import_sources) == 2
    kinds = {entry.get("via") for entry in import_sources}
    assert kinds == {"structured"}
    audit_payload = json.loads((output_dir / "audit_log.json").read_text(encoding="utf-8"))
    audit_sources = audit_payload["prepare_normalization"].get("import_sources", [])
    assert len(audit_sources) == 2


def test_cli_prepare_static_mode_invokes_hooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "prepare-output"
    jobspec_dir = tmp_path / "spec"
    template_dir = jobspec_dir / "extract"
    prompts_dir = template_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    template_spec_path = template_dir / "template_spec.json"
    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="slide-001",
                layout="StaticLayout",
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="slot-title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        default_text=["既定タイトル"],
                    )
                ],
            )
        ]
    )
    template_spec_path.write_text(
        json.dumps(
            TemplateSpec(
                template_path="templates/static_layout.pptx",
                extracted_at="2025-12-06T00:00:00Z",
                layouts=[],
                layout_mode="static",
                blueprint=blueprint,
            ).model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    jobspec_path = jobspec_dir / "jobspec.json"
    jobspec_payload = {
        "meta": {
            "schema_version": "1.0",
            "title": "静的テンプレ CLI",
            "template_path": "templates/static_layout.pptx",
            "template_spec_path": "extract/template_spec.json",
            "template_id": "static_layout",
        },
        "auth": {"created_by": "tester"},
        "slides": [
            {
                "id": "slide-001",
                "layout": "StaticLayout",
                "title": "S1",
            }
        ],
    }
    jobspec_path.write_text(json.dumps(jobspec_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    prepare_source_a = tmp_path / "input-a.md"
    prepare_source_a.write_text("line1", encoding="utf-8")
    prepare_source_b = tmp_path / "input-b.md"
    prepare_source_b.write_text("line2", encoding="utf-8")

    cards_path = output_dir / "prepare_card.json"
    log_path = output_dir / "prepare_log.json"
    ai_log_path = output_dir / "prepare_ai_log.json"
    meta_path = output_dir / "meta.json"
    story_outline_path = output_dir / "story_outline.json"
    audit_path = output_dir / "audit.json"
    for file_path in (cards_path, log_path, ai_log_path, meta_path, story_outline_path, audit_path):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("{}", encoding="utf-8")

    class DummyHookManager:
        def __init__(self) -> None:
            self.stage_calls: list[dict[str, str]] = []
            self.slide_calls: list[tuple[str, list[dict[str, Any]], dict[str, str]]] = []

        def run_stage_hook(self, stage: str, env: dict[str, str]) -> tuple[bool, bool]:
            self.stage_calls.append(dict(env))
            return True, True

        def run_slide_hooks(
            self,
            stage: str,
            *,
            slides: list[dict[str, Any]],
            env: dict[str, str],
        ) -> None:
            self.slide_calls.append((stage, slides, dict(env)))

    hook_manager = DummyHookManager()

    def fake_run_prepare_command(config, *, dump_json):  # type: ignore[missing-annotations]
        return PrepareCommandResult(
            cards_path=cards_path,
            log_path=log_path,
            ai_log_path=ai_log_path,
            meta_path=meta_path,
            story_outline_path=story_outline_path,
            audit_path=audit_path,
            messages=["prepare executed"],
        )

    monkeypatch.setattr("pptx_generator.cli_commands.prepare.run_prepare_command", fake_run_prepare_command)
    monkeypatch.setattr(
        "pptx_generator.cli_commands.prepare.load_hooks_for_template_id",
        lambda template_id: hook_manager,
    )

    args = [
        "prepare",
        f"{prepare_source_a},{prepare_source_b}",
        "--mode",
        "static",
        "--jobspec",
        str(jobspec_path),
        "--output",
        str(output_dir),
    ]

    result = runner.invoke(app, args, catch_exceptions=False)

    assert result.exit_code == 0
    assert hook_manager.stage_calls
    stage_env = hook_manager.stage_calls[0]
    assert stage_env["PPTX_STAGE"] == STAGE_PREPARE
    assert stage_env["PPTX_TEMPLATE_ID"] == "static_layout"
    assert stage_env["PPTX_PREPARE_PATH"] == str(prepare_source_a)
    assert stage_env["PPTX_PREPARE_INPUTS"].splitlines() == [str(prepare_source_a), str(prepare_source_b)]

    assert hook_manager.slide_calls
    slide_stage, slide_contexts, slide_env = hook_manager.slide_calls[0]
    assert slide_stage == STAGE_PREPARE
    assert slide_env["PPTX_PREPARE_CARD_PATH"] == str(cards_path)
    assert getattr(slide_contexts[0], "slide_id") == "slide-001"


def test_prepare_static_fallback_without_chapters(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    policy_set = load_prepare_policy_set(Path("config/prepare_policies/default.json"))
    orchestrator = PrepareAIOrchestrator(policy_set, llm_client=MockPrepareLLMClient())

    source = PrepareSourceDocument(
        meta=PrepareSourceMeta(title="静的テンプレ検証", prepare_id="static-fallback"),
        chapters=[],
        raw_text="A. 静的テンプレの概要\nB. 主なポイント\nC. まとめ",
    )
    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="blueprint-01",
                layout="StaticLayout",
                required=True,
                intent_tags=["overview"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="blueprint-01.title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        intent_tags=["headline"],
                    ),
                    TemplateBlueprintSlot(
                        slot_id="blueprint-01.body",
                        anchor="Body",
                        content_type="text",
                        required=False,
                        intent_tags=["details"],
                    ),
                ],
            )
        ]
    )

    policy = policy_set.get_policy(None)
    cards, slot_summary, ai_records, prompt_usage = orchestrator._build_cards_static(
        source=source,
        policy=policy,
        blueprint=blueprint,
        page_limit=None,
        prompt_overrides=[],
        slide_sources=None,
        slide_input_refs=None,
    )

    assert len(cards) == 2
    assert slot_summary["required_total"] == 1
    assert slot_summary["required_fulfilled"] == 1
    assert cards[0].meta["blueprint"]["fulfilled"] is True
    # fallback経路でも LLM 呼び出しが slot 数分行われる
    assert len(ai_records) == 1
    assert ai_records[0].batch_card_ids == ["blueprint-01-title", "blueprint-01-body"]
    assert prompt_usage == []


class SlotDroppingPrepareMock(MockPrepareLLMClient):
    """Mock that omits the last slot from the response."""

    def generate(self, prompt: str, *, model_hint: str | None = None) -> PrepareLLMResult:  # noqa: D401
        result = super().generate(prompt, model_hint=model_hint)
        payload = json.loads(result.text)
        slots = payload.get("slots") or []
        if isinstance(slots, list) and slots:
            slots = slots[:-1]
        text = json.dumps({"slots": slots}, ensure_ascii=False)
        return PrepareLLMResult(text=text, model=result.model, warnings=result.warnings, tokens=result.tokens)


def test_prepare_static_slot_missing_response(monkeypatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    policy_set = load_prepare_policy_set(Path("config/prepare_policies/default.json"))
    orchestrator = PrepareAIOrchestrator(policy_set, llm_client=SlotDroppingPrepareMock())

    source = PrepareSourceDocument(
        meta=PrepareSourceMeta(title="Slot 欠損", prepare_id="slot-missing"),
        chapters=[],
        raw_text="A. 要約のみ",
    )
    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="bp-slot",
                layout="StaticLayout",
                required=True,
                intent_tags=["overview"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="bp-slot.title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        intent_tags=["headline"],
                    ),
                    TemplateBlueprintSlot(
                        slot_id="bp-slot.body",
                        anchor="Body",
                        content_type="text",
                        required=False,
                        intent_tags=["details"],
                    ),
                ],
            )
        ]
    )

    policy = policy_set.get_policy(None)
    cards, slot_summary, _, prompt_usage = orchestrator._build_cards_static(
        source=source,
        policy=policy,
        blueprint=blueprint,
        page_limit=None,
        prompt_overrides=[],
        slide_sources=None,
        slide_input_refs=None,
    )

    assert len(cards) == 2
    assert cards[1].meta["blueprint"]["fulfilled"] is False
    assert slot_summary["optional_total"] == 1
    assert slot_summary["optional_used"] == 0
    assert prompt_usage == []


def test_build_cards_static_applies_prompt_override(monkeypatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    policy_set = load_prepare_policy_set(Path("config/prepare_policies/default.json"))
    orchestrator = PrepareAIOrchestrator(policy_set, llm_client=MockPrepareLLMClient())

    source = PrepareSourceDocument(
        meta=PrepareSourceMeta(title="Override テスト", prepare_id="override-test"),
        chapters=[],
        raw_text="概要のみ",
    )
    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="override-slide",
                layout="OverrideLayout",
                required=True,
                intent_tags=["overview"],
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="override-slide.title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        intent_tags=["headline"],
                    )
                ],
            )
        ]
    )

    override = StaticPromptOverride(
        slide_id="override-slide",
        slide_index=1,
        instructions="- ROI を 2 行で列挙",
        template_path=".pptx/extract/prompts/01_override.md",
    )

    policy = policy_set.get_policy(None)
    cards, slot_summary, ai_records, prompt_usage = orchestrator._build_cards_static(
        source=source,
        policy=policy,
        blueprint=blueprint,
        page_limit=None,
        prompt_overrides=[override],
        slide_sources=None,
        slide_input_refs=None,
    )

    assert cards, "カードが生成されること"
    assert slot_summary["required_total"] == 1
    assert ai_records[0].prompt_template_path == override.template_path
    assert ai_records[0].prompt_template_instructions == override.instructions
    assert prompt_usage == [
        {
            "slide_id": "override-slide",
            "slide_index": 1,
            "template_path": override.template_path,
        }
    ]


def _encode_data_uri(text: str) -> str:
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"data:text/plain;base64,{payload}"


def test_load_prepare_inputs_assigns_unique_import_ids() -> None:
    first = _encode_data_uri("# 見出し\n最初の本文です。")
    second = _encode_data_uri("# セカンド\n別の本文です。")

    document, metadata, messages = _load_prepare_inputs((first, second))

    assert document is not None
    import_ids = [chapter.id for chapter in document.chapters if chapter.id.startswith("import-")]
    assert len(import_ids) >= 2
    assert len(import_ids) == len(set(import_ids))
    assert metadata, "各インポートソースのメタ情報が含まれること"
    assert any("インポートを完了しました" in message for message in messages)


def test_load_prepare_input_rejects_http_protocol() -> None:
    with pytest.raises(PrepareCommandError):
        _load_prepare_input("http://example.com/sample", object())  # type: ignore[arg-type]


def _build_prepare_card(
    *,
    card_id: str,
    headline: str,
    body_lines: list[str],
    notes: list[str] | None = None,
) -> PrepareCard:
    body_blocks = [PrepareBodyBlock(type="paragraph", text=line) for line in body_lines]
    note_entries = [PrepareNoteEntry(type="note", text=text) for text in (notes or [])]
    content = PrepareCardContent(headline=headline, body=body_blocks, notes=note_entries)
    return PrepareCard(
        card_id=card_id,
        order=1,
        role=PrepareCardRole(story_phase="introduction", intent_tags=["body"]),
        content=content,
        meta={"blueprint": {"slot_id": card_id}},
    )


def test_draft_structuring_routes_notes_to_slide_notes() -> None:
    step = DraftStructuringStep()
    slot = TemplateBlueprintSlot(
        slot_id="system_layout-01.slot09",
        anchor="Date_dept",
        content_type="text",
        required=True,
        intent_tags=["body"],
    )
    card = _build_prepare_card(
        card_id="systemlayout-01-slot09",
        headline="Date",
        body_lines=["2025-11 | 提案自動化プラットフォーム（R&D）"],
        notes=["日付は作成月、部門はプロジェクトの性格に合わせて調整可。"],
    )
    elements: dict[str, object] = {}
    lines = step._card_to_lines(card)
    step._assign_slot_to_elements(elements, slot, card, lines)

    assert elements["Date_dept"] == ["2025-11 | 提案自動化プラットフォーム（R&D）"]
    assert "note" not in elements

    step._merge_slide_notes(elements, card.notes_text())
    assert "note" in elements
    assert "日付は作成月" in elements["note"]
    assert "2025-11" not in elements["note"]


def test_draft_structuring_builds_table_payload_for_table_slots() -> None:
    step = DraftStructuringStep()
    slot = TemplateBlueprintSlot(
        slot_id="system_layout-01.slot05",
        anchor="Items",
        content_type="table",
        required=True,
        intent_tags=[],
    )
    card = _build_prepare_card(
        card_id="systemlayout-01-slot05",
        headline="Items",
        body_lines=["品質基準を可視化", "承認プロセスを共通化"],
    )
    elements: dict[str, object] = {}
    lines = step._card_to_lines(card)
    step._assign_slot_to_elements(elements, slot, card, lines)

    table_payload = elements["Items"]
    assert table_payload["headers"] == ["項目"]
    assert table_payload["rows"] == [["品質基準を可視化"], ["承認プロセスを共通化"]]
