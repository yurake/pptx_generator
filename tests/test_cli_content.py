from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import app


SAMPLE_BRIEF = Path("samples/contents/sample_import_content_summary.txt")


def test_content_generates_brief_outputs(tmp_path) -> None:
    output_dir = tmp_path / "brief"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "content",
            str(SAMPLE_BRIEF),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    brief_dir = output_dir
    cards_path = brief_dir / "brief_cards.json"
    log_path = brief_dir / "brief_log.json"
    ai_log_path = brief_dir / "brief_ai_log.json"
    meta_path = brief_dir / "ai_generation_meta.json"
    outline_path = brief_dir / "brief_story_outline.json"
    audit_path = brief_dir / "audit_log.json"

    for path in [cards_path, log_path, ai_log_path, meta_path, outline_path, audit_path]:
        assert path.exists(), f"{path} が生成されていること"

    cards_payload = json.loads(cards_path.read_text(encoding="utf-8"))
    assert cards_payload["brief_id"]
    assert len(cards_payload["cards"]) == 4
    first_card = cards_payload["cards"][0]
    assert first_card["status"] == "draft"
    assert first_card["story"]["phase"] == "introduction"

    log_payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert log_payload == []

    outline_payload = json.loads(outline_path.read_text(encoding="utf-8"))
    assert len(outline_payload["chapters"]) == 4

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    brief_meta = audit_payload["brief_normalization"]
    assert brief_meta["policy_id"]
    assert brief_meta["statistics"]["cards_total"] == 4
    outputs = brief_meta["outputs"]
    assert outputs["brief_cards"].endswith("brief_cards.json")


def test_content_requires_valid_brief(tmp_path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["content", str(invalid_path)], catch_exceptions=False)

    assert result.exit_code != 0
    assert "解析に失敗" in result.output


def test_content_respects_card_limit(tmp_path) -> None:
    output_dir = tmp_path / "limited"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "content",
            str(SAMPLE_BRIEF),
            "--output",
            str(output_dir),
            "--card-limit",
            "2",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    cards_payload = json.loads((output_dir / "brief_cards.json").read_text(encoding="utf-8"))
    assert len(cards_payload["cards"]) == 2
    meta_payload = json.loads((output_dir / "ai_generation_meta.json").read_text(encoding="utf-8"))
    assert meta_payload["statistics"]["cards_total"] == 2
