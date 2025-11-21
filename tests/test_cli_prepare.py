from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import app
from pptx_generator.models import TemplateBlueprint, TemplateBlueprintSlide, TemplateBlueprintSlot
from pptx_generator.prepare.llm_client import MockPrepareLLMClient
from pptx_generator.prepare.orchestrator import PrepareAIOrchestrator
from pptx_generator.prepare.policy import load_prepare_policy_set
from pptx_generator.prepare.source import PrepareSourceDocument, PrepareSourceMeta


SAMPLE_PREPARE_SOURCE = Path("samples/contents/sample_import_content_summary.txt")


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
    cards, slot_summary, ai_records = orchestrator._build_cards_static(
        source=source,
        policy=policy,
        blueprint=blueprint,
        page_limit=None,
    )

    assert len(cards) == 2
    assert slot_summary["required_total"] == 1
    assert slot_summary["required_fulfilled"] == 1
    assert cards[0].meta["blueprint"]["fulfilled"] is True
    # fallback経路でも LLM 呼び出しが slot 数分行われる
    assert len(ai_records) == 2
