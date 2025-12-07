import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from pptx_generator.cli import app


ROOT_DIR = Path(__file__).resolve().parents[2]


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
                "locale": "ja-JP",
                "template_path": "templates/templates.pptx",
                "layouts_path": "layouts.jsonl",
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

    template_src = ROOT_DIR / "samples" / "templates" / "templates.pptx"
    template_dst = spec_path.parent / "templates" / "templates.pptx"
    template_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_src, template_dst)

    layouts_path = spec_path.parent / "layouts.jsonl"
    layouts_path.write_text(
        json.dumps(
            {
                "layout_id": "Title",
                "usage_tags": ["intro"],
                "text_hint": {"max_lines": 5},
                "media_hint": {"allow_table": False},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return spec_path


@pytest.fixture()
def prepare_cards(tmp_path: Path) -> Path:
    cards_path = tmp_path / "prepare_card.json"
    _write_json(
        cards_path,
        {
            "prepare_id": "prepare-test",
            "cards": [
                {
                    "card_id": "s01",
                    "order": 1,
                    "role": {
                        "story_phase": "introduction",
                        "intent_tags": ["overview"],
                    },
                    "content": {
                        "title": "Overview",
                        "headline": "Overview summary",
                        "body": [
                            {"type": "paragraph", "text": "Line 1"},
                            {"type": "paragraph", "text": "Line 2"},
                        ],
                        "notes": [],
                    },
                    "meta": {},
                }
            ],
            "story_context": {"chapters": []},
            "meta": {
                "prepare_log_path": "prepare_log.json",
                "ai_generation_meta_path": "ai_generation_meta.json",
                "prepare_ai_log_path": "prepare_ai_log.json",
            },
        },
    )
    _write_json(tmp_path / "prepare_log.json", [])
    _write_json(
        tmp_path / "ai_generation_meta.json",
        {
            "prepare_id": "prepare-test",
            "generated_at": "2025-11-02T00:00:00Z",
            "policy_id": "prepare-default",
            "input_hash": "sha256:d41d8cd98f00b204e9800998ecf8427e",
            "cards": [],
            "statistics": {"cards_total": 1},
        },
    )
    _write_json(tmp_path / "prepare_ai_log.json", [])
    return cards_path


@pytest.fixture()
def prepare_log(tmp_path: Path) -> Path:
    log_path = tmp_path / "prepare_log.json"
    _write_json(log_path, [])
    return log_path


@pytest.fixture()
def prepare_meta(tmp_path: Path) -> Path:
    meta_path = tmp_path / "ai_generation_meta.json"
    _write_json(
        meta_path,
        {
            "prepare_id": "prepare-test",
            "generated_at": "2025-11-02T00:00:00Z",
            "policy_id": "prepare-default",
            "input_hash": "sha256:d41d8cd98f00b204e9800998ecf8427e",
            "cards": [],
            "statistics": {"cards_total": 1},
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
                "layout_name": "Overview One Column",
                "usage_tags": ["overview"],
                "text_hint": {"max_chars": 800, "max_lines": 5},
                "media_hint": {"allow_table": True, "allow_chart": False, "allow_image": True},
                "placeholders": [
                    {
                        "name": "Title",
                        "type": "title",
                        "bbox": {"x": 0, "y": 0, "width": 1000, "height": 300},
                        "shape_type": "LayoutPlaceholder",
                        "flags": [],
                    },
                    {
                        "name": "Body",
                        "type": "body",
                        "bbox": {"x": 0, "y": 400, "width": 1000, "height": 600},
                        "shape_type": "LayoutPlaceholder",
                        "flags": [],
                    },
                ],
                "placeholder_summary": {
                    "counts": {"body": 1, "title": 1},
                    "area_ratio": {"title": 0.333, "body": 0.667},
                    "details": [
                        {"name": "Body", "type": "body", "area_ratio": 0.667},
                        {"name": "Title", "type": "title", "area_ratio": 0.333},
                    ],
                    "attributes": {
                        "total": 2,
                        "has_title": True,
                        "has_body": True,
                        "has_table": False,
                        "has_chart": False,
                        "has_visual": False,
                    },
                },
                "heuristic": {
                    "tags": ["content"],
                    "reasons": ["placeholder:type=body"],
                    "has_title_placeholder": True,
                    "has_body_placeholder": True,
                    "title_from_name": False,
                },
                "static_rules": [],
                "meta": {
                    "heuristic_reason": "placeholder:type=body; template_ai:fallback"
                },
                "version": "1.1.0",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return layouts


def test_compose_resolves_paths_from_jobspec_meta(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    spec_path = tmp_path / "input" / "jobspec.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    layouts_relative = "layouts/layouts.jsonl"
    _write_json(
        spec_path,
        {
            "meta": {
                "schema_version": "1.1",
                "title": "Auto Template Spec",
                "client": "Example Co.",
                "template_path": "templates/templates.pptx",
                "layouts_path": layouts_relative,
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

    template_src = ROOT_DIR / "samples" / "templates" / "templates.pptx"
    template_dst = spec_path.parent / "templates" / "templates.pptx"
    template_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_src, template_dst)

    prepare_dir = tmp_path / "prepare"
    prepare_dir.mkdir(parents=True, exist_ok=True)
    cards_path = prepare_dir / "prepare_card.json"
    _write_json(
        cards_path,
        {
            "prepare_id": "prepare-1",
            "cards": [
                {
                    "card_id": "intro",
                    "order": 1,
                    "role": {
                        "story_phase": "introduction",
                        "intent_tags": ["intro"],
                    },
                    "content": {
                        "title": "Intro",
                        "headline": "Intro message",
                        "body": [
                            {"type": "paragraph", "text": "Line 1"},
                        ],
                        "notes": [],
                    },
                    "meta": {},
                }
            ],
            "story_context": {"chapters": []},
        },
    )
    prepare_log_path = prepare_dir / "prepare_log.json"
    _write_json(prepare_log_path, [])
    prepare_meta_path = prepare_dir / "ai_generation_meta.json"
    _write_json(
        prepare_meta_path,
        {
            "prepare_id": "prepare-1",
            "generated_at": "2025-11-02T00:00:00Z",
            "policy_id": "prepare-default",
            "input_hash": "sha256:d41d8cd98f00b204e9800998ecf8427e",
            "cards": [],
            "statistics": {"cards_total": 1},
        },
    )

    layouts_path = spec_path.parent / layouts_relative
    layouts_path.parent.mkdir(parents=True, exist_ok=True)
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

    compose_dir = tmp_path / "compose"

    result = runner.invoke(
        app,
        [
            "compose",
            str(spec_path),
            "--prepare-cards",
            str(cards_path),
            "--output",
            str(compose_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    draft_dir = compose_dir / "draft"
    assert draft_dir.exists()
    assert (compose_dir / "generate_ready.json").exists()


def test_mapping_resolves_layouts_from_jobspec_meta(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    spec_path = tmp_path / "input" / "jobspec.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    layouts_relative = "layouts/layouts.jsonl"
    _write_json(
        spec_path,
        {
            "meta": {
                "schema_version": "1.1",
                "title": "Mapping Spec",
                "client": "Example Co.",
                "template_path": "templates/templates.pptx",
                "layouts_path": layouts_relative,
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

    template_src = ROOT_DIR / "samples" / "templates" / "templates.pptx"
    template_dst = spec_path.parent / "templates" / "templates.pptx"
    template_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_src, template_dst)

    layouts_path = spec_path.parent / layouts_relative
    layouts_path.parent.mkdir(parents=True, exist_ok=True)
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

    cards_path = tmp_path / "prepare_card.json"
    _write_json(
        cards_path,
        {
            "prepare_id": "prepare-1",
            "cards": [
                {
                    "card_id": "intro",
                    "order": 1,
                    "role": {
                        "story_phase": "introduction",
                        "intent_tags": ["intro"],
                    },
                    "content": {
                        "title": "Intro",
                        "headline": "Intro message",
                        "body": [
                            {"type": "paragraph", "text": "Line 1"},
                        ],
                        "notes": [],
                    },
                    "meta": {},
                }
            ],
            "story_context": {"chapters": []},
            "meta": {
                "prepare_log_path": "prepare_log.json",
                "ai_generation_meta_path": "ai_generation_meta.json",
            },
        },
    )

    prepare_log_path = tmp_path / "prepare_log.json"
    _write_json(prepare_log_path, [])
    prepare_meta_path = tmp_path / "ai_generation_meta.json"
    _write_json(
        prepare_meta_path,
        {
            "prepare_id": "prepare-1",
            "generated_at": "2025-11-18T00:00:00Z",
            "policy_id": "prepare-default",
            "input_hash": "sha256:dummy",
            "cards": [
                {
                    "card_id": "intro",
                    "story_phase": "introduction",
                    "intent_tags": ["intro"],
                    "content_hash": "sha256:dummy",
                    "body_blocks": 1,
                    "note_entries": 0,
                }
            ],
            "statistics": {"cards_total": 1},
            "mode": "dynamic",
            "slot_coverage": {},
            "constraints": {},
        },
    )

    output_dir = tmp_path / "compose"

    result = runner.invoke(
        app,
        [
            "mapping",
            str(spec_path),
            "--prepare-cards",
            str(cards_path),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    draft_dir = output_dir / "draft"
    assert draft_dir.exists()
    assert (output_dir / "generate_ready.json").exists()


def test_outline_with_layout_reasons(
    runner: CliRunner,
    sample_spec: Path,
    prepare_cards: Path,
    prepare_log: Path,
    prepare_meta: Path,
    tmp_path: Path,
) -> None:
    _ = (prepare_log, prepare_meta)
    output_dir = tmp_path / "draft"
    result = runner.invoke(
        app,
        [
            "outline",
            str(sample_spec),
            "--output",
            str(output_dir),
            "--show-layout-reasons",
            "--prepare-cards",
            str(prepare_cards),
        ],
    )

    assert result.exit_code == 0, result.output
    draft_path = output_dir / "draft_draft.json"
    assert draft_path.exists()
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    slide = draft["sections"][0]["slides"][0]
    assert "layout_score_detail" in slide
    assert slide["layout_score_detail"]["uses_tag"] >= 0
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
    candidate = mapping_log[0]["candidates"][0]
    detail = candidate.get("detail")
    assert detail and "ai_recommendation" in detail
    assert detail["uses_tag"] >= 0
    assert "ai_response" in mapping_log[0]
    assert mapping_log[0]["ai_response"]["reasons"]
