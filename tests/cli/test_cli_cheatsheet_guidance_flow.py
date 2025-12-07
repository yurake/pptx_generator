"""README の CLI チートシート順序を検証する統合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pptx_generator.cli import app

SAMPLE_TEMPLATE = Path("samples/templates/templates.pptx")
SAMPLE_PREPARE_SOURCE = Path("samples/input/pitch.md")


@pytest.mark.skipif(
    not SAMPLE_TEMPLATE.exists(),
    reason="サンプルテンプレートが存在しない",
)
def test_cli_cheatsheet_flow(tmp_path: Path) -> None:
    """CLI チートシートを順に呼び出し、現状の入出力期待値をドキュメント化する。"""

    runner = CliRunner()

    release_dir = tmp_path / "release"
    tpl_release = runner.invoke(
        app,
        [
            "tpl-release",
            "--template",
            str(SAMPLE_TEMPLATE),
            "--brand",
            "demo",
            "--version",
            "v1",
            "--output",
            str(release_dir),
        ],
        catch_exceptions=False,
    )

    assert tpl_release.exit_code == 0

    template_release_path = release_dir / "template_release.json"
    assert template_release_path.exists()
    release_payload = json.loads(
        template_release_path.read_text(encoding="utf-8"))
    assert release_payload.get("brand") == "demo"
    assert release_payload.get("version") == "v1"

    extract_root = tmp_path / "template"
    template_result = runner.invoke(
        app,
        [
            "tpl-extract",
            "--template",
            str(SAMPLE_TEMPLATE),
            "--output",
            str(extract_root),
        ],
        catch_exceptions=False,
    )

    assert template_result.exit_code == 0

    template_spec_path = extract_root / "template_spec.json"
    jobspec_path = extract_root / "jobspec.json"
    branding_path = extract_root / "branding.json"
    layouts_path = extract_root / "layouts.jsonl"
    diagnostics_path = extract_root / "diagnostics.json"

    assert template_spec_path.exists()
    assert jobspec_path.exists()
    assert branding_path.exists()
    assert layouts_path.exists()
    assert diagnostics_path.exists()
    jobspec_payload = json.loads(jobspec_path.read_text(encoding="utf-8"))
    assert "meta" in jobspec_payload

    content_output = tmp_path / "prepare"
    content_cmd = runner.invoke(
        app,
        [
            "prepare",
            str(SAMPLE_PREPARE_SOURCE),
            "--mode",
            "dynamic",
            "--output",
            str(content_output),
        ],
        catch_exceptions=False,
    )

    assert content_cmd.exit_code == 0

    prepare_cards_path = content_output / "prepare_card.json"
    prepare_log_path = content_output / "prepare_log.json"
    prepare_meta_path = content_output / "ai_generation_meta.json"
    assert prepare_cards_path.exists()
    assert prepare_log_path.exists()
    assert prepare_meta_path.exists()

    cards_payload = json.loads(prepare_cards_path.read_text(encoding="utf-8"))
    slides = []
    for index, card in enumerate(cards_payload.get("cards", []), start=1):
        card_id = card.get("card_id") or f"card-{index:03d}"
        content = card.get("content") or {}
        title = (content.get("title") or content.get("headline") or card_id)[:25]
        slides.append(
            {
                "id": card_id,
                "layout": "Content" if index > 1 else "Title",
                "title": title,
            }
        )

    matching_jobspec_path = tmp_path / "jobspec_matching_cards.json"
    meta_payload = dict(jobspec_payload.get("meta") or {})
    meta_payload.setdefault("schema_version", "1.0")
    meta_payload.setdefault("title", "Matching Spec")
    meta_payload.setdefault("locale", "ja-JP")
    meta_payload["template_path"] = str(SAMPLE_TEMPLATE.resolve())
    meta_payload["layouts_path"] = str(layouts_path.resolve())

    auth_payload = jobspec_payload.get("auth")
    if not isinstance(auth_payload, dict):
        auth_payload = {"created_by": "cheatsheet"}

    matching_jobspec_path.write_text(
        json.dumps(
            {
                "meta": meta_payload,
                "auth": auth_payload,
                "slides": slides,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    compose_output_root = tmp_path / "compose"
    compose_cmd = runner.invoke(
        app,
        [
            "compose",
            str(matching_jobspec_path),
            "--output",
            str(compose_output_root / "gen"),
            "--prepare-cards",
            str(prepare_cards_path),
        ],
        catch_exceptions=False,
    )

    assert compose_cmd.exit_code == 0, compose_cmd.output

    generate_ready_path = compose_output_root / "gen" / "generate_ready.json"
    assert generate_ready_path.exists()
    assert (compose_output_root / "gen" / "draft").exists()
