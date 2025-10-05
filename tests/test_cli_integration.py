"""CLI の統合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from pptx_generator.cli import app
from pptx_generator.models import JobSpec


def test_cli_run_generates_outputs(tmp_path) -> None:
    spec_path = Path("samples/sample_spec.json")
    workdir = tmp_path / "work"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run",
            str(spec_path),
            "--workdir",
            str(workdir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    spec = JobSpec.parse_file(spec_path)

    outputs_dir = workdir / "outputs"
    pptx_path = outputs_dir / "proposal.pptx"
    analysis_path = outputs_dir / "analysis.json"

    assert pptx_path.exists()
    assert analysis_path.exists()

    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert payload.get("slides") == len(spec.slides)
    assert isinstance(payload.get("issues"), list)
    assert isinstance(payload.get("fixes"), list)
    assert payload.get("meta", {}).get("title") == spec.meta.title

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if slide_spec.title is None:
            continue
        actual = slide.shapes.title.text if slide.shapes.title else None
        assert actual == slide_spec.title

    agenda_slide = presentation.slides[1]
    tables = [shape for shape in agenda_slide.shapes if getattr(shape, "has_table", False)]
    assert tables, "テーブルが描画されていること"
    images = [shape for shape in agenda_slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert images, "画像が描画されていること"

    kpi_slide = presentation.slides[2]
    charts = [shape for shape in kpi_slide.shapes if getattr(shape, "has_chart", False)]
    assert charts, "チャートが描画されていること"


def test_cli_run_supports_template(tmp_path) -> None:
    spec_path = Path("samples/sample_spec.json")
    workdir = tmp_path / "work-template"
    template_path = tmp_path / "template.pptx"

    template = Presentation()
    template.save(template_path)

    spec = JobSpec.parse_file(spec_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--template",
            str(template_path),
            "--output",
            "with-template.pptx",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    pptx_path = workdir / "outputs" / "with-template.pptx"
    analysis_path = workdir / "outputs" / "analysis.json"
    assert pptx_path.exists()
    assert analysis_path.exists()

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if slide_spec.title is None:
            continue
        actual = slide.shapes.title.text if slide.shapes.title else None
        assert actual == slide_spec.title

    agenda_slide = presentation.slides[1]
    tables = [shape for shape in agenda_slide.shapes if getattr(shape, "has_table", False)]
    assert tables
