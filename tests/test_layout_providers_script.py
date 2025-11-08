"""Integration test for layout provider validation script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
def test_layout_provider_script_runs_when_env_present() -> None:
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if not env_file.exists():
        pytest.skip(".env が存在しないためレイアウトプロバイダ検証をスキップします")

    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", ".uv-cache")

    result = subprocess.run(
        ["bash", "scripts/test_layout_providers.sh"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(
            "layout provider script failed with exit code "
            f"{result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    combined_log = f"{result.stdout}\n{result.stderr}".strip()
    for level in ("WARNING", "ERROR", "CRITICAL"):
        assert level not in combined_log, (
            f"検証スクリプト実行時に {level} ログが出力されました:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
