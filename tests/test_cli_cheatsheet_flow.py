"""README の CLI チートシート順序を検証する統合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pptx_generator.cli import app

SAMPLE_TEMPLATE = Path("samples/templates/templates.pptx")
SAMPLE_CONTENT_SOURCE = Path("samples/contents/sample_import_content.txt")
SAMPLE_CONTENT_APPROVED = Path("samples/json/sample_content_approved.json")
SAMPLE_CONTENT_REVIEW_LOG = Path("samples/json/sample_content_review_log.json")


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
    release_payload = json.loads(template_release_path.read_text(encoding="utf-8"))
    assert release_payload.get("brand") == "demo"
    assert release_payload.get("version") == "v1"

    template_result = runner.invoke(
        app,
        [
            "template",
            str(SAMPLE_TEMPLATE),
            "--output",
            str(tmp_path / "template"),
        ],
        catch_exceptions=False,
    )

    assert template_result.exit_code != 0
    assert "No such command 'template'" in template_result.output

    extract_root = tmp_path / "extract"
    tpl_extract = runner.invoke(
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

    assert tpl_extract.exit_code == 0

    layout_validate = runner.invoke(
        app,
        [
            "layout-validate",
            "--template",
            str(SAMPLE_TEMPLATE),
            "--output",
            str(extract_root / "validation"),
        ],
        catch_exceptions=False,
    )

    assert layout_validate.exit_code == 0

    template_spec_path = extract_root / "template_spec.json"
    jobspec_path = extract_root / "jobspec.json"
    branding_path = extract_root / "branding.json"
    layouts_path = extract_root / "validation" / "layouts.jsonl"

    assert template_spec_path.exists()
    assert jobspec_path.exists()
    assert branding_path.exists()
    assert layouts_path.exists()

    jobspec_payload = json.loads(jobspec_path.read_text(encoding="utf-8"))
    assert "meta" in jobspec_payload

    content_output = tmp_path / "content"
    content_cmd = runner.invoke(
        app,
        [
            "content",
            str(jobspec_path),
            "--content-source",
            str(SAMPLE_CONTENT_SOURCE),
            "--output",
            str(content_output),
        ],
        catch_exceptions=False,
    )

    assert content_cmd.exit_code == 2
    assert "スキーマ検証に失敗しました" in content_cmd.output

    compose_output_root = tmp_path / "compose"
    compose_cmd = runner.invoke(
        app,
        [
            "compose",
            str(jobspec_path),
            "--content-approved",
            str(SAMPLE_CONTENT_APPROVED),
            "--content-review-log",
            str(SAMPLE_CONTENT_REVIEW_LOG),
            "--draft-output",
            str(compose_output_root / "draft"),
            "--output",
            str(compose_output_root / "gen"),
            "--layouts",
            str(layouts_path),
        ],
        catch_exceptions=False,
    )

    assert compose_cmd.exit_code == 2
    assert "スキーマ検証に失敗しました" in compose_cmd.output
