"""Integration test for template extraction CLI."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_template_extraction_script_runs_successfully() -> None:
    project_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", ".uv-cache")

    result = subprocess.run(
        ["bash", "scripts/test_template_extraction.sh"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise AssertionError(
            "template extraction script failed with exit code "
            f"{result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    combined = f"{result.stdout}\n{result.stderr}".strip()
    for level in ("WARNING", "ERROR", "CRITICAL"):
        assert level not in combined, (
            f"テンプレート抽出スクリプト実行時に {level} ログが出力されました:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
