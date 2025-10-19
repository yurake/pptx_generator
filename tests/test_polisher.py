"""PolisherStep の動作検証テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pptx_generator.models import JobAuth, JobMeta, JobSpec
from pptx_generator.pipeline import (PipelineContext, PolisherError,
                                     PolisherOptions, PolisherStep)


def _build_context(tmp_path: Path) -> tuple[PipelineContext, Path]:
    spec = JobSpec(
        meta=JobMeta(
            schema_version="1.1",
            title="Polisher テスト",
            client="Test",
            author="営業部",
            created_at="2025-10-18",
            theme="corporate",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[],
    )
    context = PipelineContext(spec=spec, workdir=tmp_path)
    pptx_path = tmp_path / "output.pptx"
    pptx_path.write_bytes(b"pptx-initial")
    context.add_artifact("pptx_path", pptx_path)
    return context, pptx_path


def test_polisher_disabled_skips_execution(tmp_path: Path) -> None:
    context, _ = _build_context(tmp_path)
    step = PolisherStep(PolisherOptions(enabled=False))

    step.run(context)

    metadata = context.require_artifact("polisher_metadata")
    assert metadata["status"] == "disabled"
    assert metadata["enabled"] is False


def test_polisher_missing_executable_raises(tmp_path: Path) -> None:
    context, _ = _build_context(tmp_path)
    step = PolisherStep(PolisherOptions(enabled=True))

    with pytest.raises(PolisherError):
        step.run(context)


def test_polisher_executes_stub_command(tmp_path: Path) -> None:
    context, pptx_path = _build_context(tmp_path)
    rules_path = tmp_path / "polisher-rules.json"
    rules_path.write_text("{}", encoding="utf-8")

    script_path = tmp_path / "polisher_stub.py"
    script_path.write_text(
        "\n".join(
            [
                "import argparse",
                "import json",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--rules', required=True)",
                "args = parser.parse_args()",
                "path = Path(args.input)",
                "data = path.read_bytes()",
                "path.write_bytes(data)",
                "Path(args.rules).touch(exist_ok=True)",
                "print(json.dumps({'slides': 0, 'adjusted_font_size': 0, 'adjusted_color': 0}))",
            ]
        ),
        encoding="utf-8",
    )

    step = PolisherStep(
        PolisherOptions(
            enabled=True,
            executable=Path(sys.executable),
            rules_path=rules_path,
            timeout_sec=30,
            arguments=(str(script_path), "--input", "{pptx}", "--rules", "{rules}"),
        )
    )

    step.run(context)

    metadata = context.require_artifact("polisher_metadata")
    assert metadata["status"] == "success"
    assert metadata["enabled"] is True
    assert metadata["returncode"] == 0
    assert metadata["command"][0] == str(Path(sys.executable))
    summary = metadata.get("summary")
    assert isinstance(summary, dict)
    assert summary.get("slides") == 0
    assert pptx_path.read_bytes() == b"pptx-initial"
