import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from pptx_generator.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture()
def sample_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "spec.json"
    _write_json(
        spec_path,
        {
            "meta": {
                "schema_version": "1.1",
                "title": "Test Spec",
                "client": "Test",
                "locale": "ja-JP"
            },
            "auth": {"created_by": "tester"},
            "slides": [
                {
                    "id": "s01",
                    "layout": "overview",
                    "title": "Overview",
                    "bullets": [
                        {
                            "anchor": None,
                            "items": [
                                {"id": "b1", "text": "Line 1", "level": 0},
                                {"id": "b2", "text": "Line 2", "level": 0}
                            ]
                        }
                    ]
                }
            ],
        },
    )
    return spec_path


@pytest.fixture()
def brief_cards(tmp_path: Path) -> Path:
    cards_path = tmp_path / "prepare_card.json"
    _write_json(
        cards_path,
        {
            "brief_id": "brief-test",
            "cards": [
                {
                    "card_id": "s01",
                    "chapter": "Overview",
                    "message": "Overview summary",
                    "narrative": ["Line 1", "Line 2"],
                    "supporting_points": [],
                    "story": {"phase": "introduction", "goal": None, "tension": None, "resolution": None},
                    "intent_tags": ["overview"],
                    "status": "draft",
                    "autofix_applied": [],
                }
            ],
            "story_context": {"chapters": []},
        },
    )
    return cards_path


@pytest.fixture()
def brief_log(tmp_path: Path) -> Path:
    log_path = tmp_path / "brief_log.json"
    _write_json(log_path, [])
    return log_path


@pytest.fixture()
def brief_meta(tmp_path: Path) -> Path:
    meta_path = tmp_path / "ai_generation_meta.json"
    _write_json(
        meta_path,
        {
            "brief_id": "brief-test",
            "generated_at": "2025-11-02T00:00:00Z",
            "policy_id": "brief-default",
            "input_hash": "sha256:d41d8cd98f00b204e9800998ecf8427e",
            "cards": [],
            "statistics": {"cards_total": 1, "approved": 0, "returned": 0},
        },
    )
    return meta_path


@pytest.fixture()
def layouts_file(tmp_path: Path) -> Path:
    layouts = tmp_path / "layouts.jsonl"
    layouts.write_text(
        json.dumps(
            {
                "layout_id": "overview__one_col",
                "usage_tags": ["overview"],
                "text_hint": {"max_lines": 5},
                "media_hint": {"allow_table": True},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return layouts


def test_compose_resolves_template_from_jobspec_meta(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    template_src = Path("templates/jri_template.pptx").resolve()
    template_dir = tmp_path / "input" / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_dest = template_dir / "jri_template.pptx"
    shutil.copy(template_src, template_dest)

    spec_path = tmp_path / "input" / "jobspec.json"
    _write_json(
        spec_path,
        {
            "meta": {
                "schema_version": "1.1",
                "title": "Auto Template Spec",
                "client": "Example Co.",
                "template_path": "templates/jri_template.pptx",
                "locale": "ja-JP",
            },
            "auth": {"created_by": "tester"},
            "slides": [
                {
                    "id": "intro",
                    "layout": "Title",
                    "title": "Intro",
                }
            ],
        },
    )

    brief_dir = tmp_path / "prepare"
    brief_dir.mkdir(parents=True, exist_ok=True)
    cards_path = brief_dir / "prepare_card.json"
    _write_json(
        cards_path,
        {
            "brief_id": "brief-1",
            "cards": [
                {
                    "card_id": "intro",
                    "chapter": "Intro",
                    "message": "Intro message",
                    "narrative": ["Line 1"],
                    "supporting_points": [],
                    "story": {"phase": "introduction"},
                    "intent_tags": ["intro"],
                    "status": "approved",
                    "autofix_applied": [],
                }
            ],
            "story_context": {"chapters": []},
        },
    )
    brief_log_path = brief_dir / "brief_log.json"
    _write_json(brief_log_path, [])
    brief_meta_path = brief_dir / "ai_generation_meta.json"
    _write_json(
        brief_meta_path,
        {
            "brief_id": "brief-1",
            "generated_at": "2025-11-02T00:00:00Z",
            "policy_id": "brief-default",
            "input_hash": "sha256:d41d8cd98f00b204e9800998ecf8427e",
            "cards": [],
            "statistics": {"cards_total": 1, "approved": 1, "returned": 0},
        },
    )

    layouts_path = tmp_path / "layouts.jsonl"
    layouts_path.write_text(
        json.dumps(
            {
                "layout_id": "Title",
                "usage_tags": ["intro"],
                "text_hint": {"max_lines": 5},
                "media_hint": {"allow_table": False},
            }
        ),
        encoding="utf-8",
    )

    draft_dir = tmp_path / "draft"
    compose_dir = tmp_path / "compose"

    result = runner.invoke(
        app,
        [
            "compose",
            str(spec_path),
            "--brief-cards",
            str(cards_path),
            "--brief-log",
            str(brief_log_path),
            "--brief-meta",
            str(brief_meta_path),
            "--layouts",
            str(layouts_path),
            "--draft-output",
            str(draft_dir),
            "--output",
            str(compose_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (compose_dir / "generate_ready.json").exists()


def test_outline_with_layout_reasons(
    runner: CliRunner,
    sample_spec: Path,
    brief_cards: Path,
    brief_log: Path,
    brief_meta: Path,
    layouts_file: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "draft"
    result = runner.invoke(
        app,
        [
            "outline",
            str(sample_spec),
            "--layouts",
            str(layouts_file),
            "--output",
            str(output_dir),
            "--chapter-template",
            "bp-report-2025",
            "--show-layout-reasons",
            "--brief-cards",
            str(brief_cards),
            "--brief-log",
            str(brief_log),
            "--brief-meta",
            str(brief_meta),
        ],
    )

    assert result.exit_code == 0, result.output
    draft_path = output_dir / "draft_draft.json"
    assert draft_path.exists()
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    slide = draft["sections"][0]["slides"][0]
    assert "layout_score_detail" in slide
    assert slide["layout_score_detail"]["uses_tag"] > 0
    assert "ai_recommendation" in slide["layout_score_detail"]

    ready_path = output_dir / "generate_ready.json"
    assert ready_path.exists()
    ready = json.loads(ready_path.read_text(encoding="utf-8"))
    assert ready["slides"][0]["layout_id"]
    assert ready["meta"]["generated_at"]

    ready_meta_path = output_dir / "generate_ready_meta.json"
    assert ready_meta_path.exists()
    ready_meta = json.loads(ready_meta_path.read_text(encoding="utf-8"))
    assert ready_meta["statistics"]["total_slides"] == 1
    assert ready_meta["ai_recommendation"]["used"] >= 0

    mapping_log_path = output_dir / "draft_mapping_log.json"
    assert mapping_log_path.exists()
    mapping_log = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    assert mapping_log and "candidates" in mapping_log[0]
