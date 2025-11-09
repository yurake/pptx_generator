"""Integration test for layout provider validation script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


PROVIDERS = ("openai", "azure", "anthropic", "aws-claude")

REQUIRED_ENV_VARS = {
    "openai": ("OPENAI_API_KEY",),
    "azure": ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "aws-claude": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
}


def _load_env_keys(env_path: Path) -> set[str]:
    keys: set[str] = set()
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("export "):
                stripped = stripped[len("export "):].strip()
            if "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key:
                keys.add(key)
    except FileNotFoundError:
        pass
    return keys


@pytest.mark.integration
@pytest.mark.parametrize("provider", PROVIDERS)
def test_layout_provider_script_runs_when_env_present(provider: str) -> None:
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if not env_file.exists():
        pytest.skip(".env が存在しないためレイアウトプロバイダ検証をスキップします")

    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", ".uv-cache")

    env_keys = _load_env_keys(env_file)
    required_vars = REQUIRED_ENV_VARS.get(provider, ())
    missing = [var for var in required_vars if not env.get(var) and var not in env_keys]
    if missing:
        pytest.skip(
            f"環境変数 {', '.join(missing)} が設定されていないため {provider} プロバイダ検証をスキップします"
        )

    result = subprocess.run(
        ["bash", "scripts/test_layout_providers.sh", provider],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(
            f"layout provider script failed (provider={provider}) with exit code "
            f"{result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    combined_log = f"{result.stdout}\n{result.stderr}".strip()
    for level in ("WARNING", "ERROR", "CRITICAL"):
        assert level not in combined_log, (
            f"検証スクリプト実行時に {level} ログが出力されました (provider={provider}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
