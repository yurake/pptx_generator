"""AI ポリシー設定ファイルの解決ロジックを集約する。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .paths import find_config_path


@dataclass(slots=True)
class PolicyResolution:
    """ポリシーファイルの解決結果。"""

    path: Path | None
    source: str


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_POLICY_ROOT = _PACKAGE_ROOT / "config" / "ai_policies"


def _package_policy(filename: str) -> Path:
    return _PACKAGE_POLICY_ROOT / filename


def _resolve_policy(*, explicit: Path | None, env_var: str | None, package_filename: str) -> PolicyResolution:
    if explicit:
        resolved = find_config_path(explicit)
        if resolved:
            return PolicyResolution(resolved, "explicit")

    if env_var:
        env_value = os.getenv(env_var)
        if env_value:
            resolved = find_config_path(Path(env_value))
            if resolved:
                return PolicyResolution(resolved, "env")

    package_path = _package_policy(package_filename)
    if package_path.is_file():
        return PolicyResolution(package_path, "package")

    return PolicyResolution(None, "missing")


def resolve_template_ai_policy_path(path: Path | None = None) -> PolicyResolution:
    """テンプレート AI ポリシーの探索順を統一する（パッケージ同梱が既定）。"""

    return _resolve_policy(
        explicit=path,
        env_var="PPTX_TEMPLATE_AI_POLICY",
        package_filename="template.json",
    )


__all__ = [
    "PolicyResolution",
    "resolve_template_ai_policy_path",
]
