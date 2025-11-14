"""Integration test for template AI extraction script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
def test_template_ai_script_runs_successfully(tmp_path) -> None:
    project_root = Path(__file__).resolve().parent.parent
    script_path = project_root / "scripts" / "test_template_ai.sh"
    if not script_path.exists():
        pytest.skip("scripts/test_template_ai.sh が存在しないためスキップします")

    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", ".uv-cache")

    result = subprocess.run(
        ["bash", str(script_path)],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(
            "template AI integration script failed.\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    assert "Template AI extraction test passed." in result.stdout
