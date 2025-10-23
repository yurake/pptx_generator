"""テンプレート監査で使用する実行環境メタ情報の収集ヘルパ。"""

from __future__ import annotations

import platform
import subprocess
from importlib import metadata
from typing import List, Tuple

from ..models import TemplateReleaseEnvironment

DEFAULT_TIMEOUT_SECONDS = 5.0


def collect_environment_info() -> Tuple[TemplateReleaseEnvironment, List[str]]:
    """実行環境メタ情報を収集し、取得できなかった項目は警告として返す。"""

    warnings: list[str] = []

    python_version = platform.python_version()
    system = platform.platform()
    pptx_generator_version = _load_package_version("pptx-generator") or "local"

    libreoffice_version = _run_command(["soffice", "--headless", "--version"])
    if libreoffice_version is None:
        warnings.append(
            "environment: LibreOffice (soffice --headless --version) のバージョン取得に失敗しました"
        )

    dotnet_version = _run_command(["dotnet", "--version"])
    if dotnet_version is None:
        warnings.append(
            "environment: dotnet --version の実行に失敗しました"
        )

    environment = TemplateReleaseEnvironment(
        python_version=python_version,
        platform=system,
        pptx_generator_version=pptx_generator_version,
        libreoffice_version=_first_line_or_none(libreoffice_version),
        dotnet_sdk_version=_first_line_or_none(dotnet_version),
    )
    return environment, warnings


def _load_package_version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def _run_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError, ValueError):
        return None

    output = (result.stdout or result.stderr or "").strip()
    return output or None


def _first_line_or_none(text: str | None) -> str | None:
    if not text:
        return None
    return text.splitlines()[0].strip()
