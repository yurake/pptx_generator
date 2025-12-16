"""AI ポリシー設定ファイルの解決ロジックを集約する。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .paths import find_config_path


@dataclass(slots=True)
class PolicyResolution:
    """ポリシーファイルの解決結果。"""

    path: Path | None
    source: str


_TEMPLATE_CANDIDATES: tuple[str, ...] = (
    "config/ai_policies/template.json",
    "config/template_ai_policies.json",
)
_LAYOUT_CANDIDATES: tuple[str, ...] = (
    "config/ai_policies/layout.json",
    "config/layout_ai_policies.json",
)
_SLIDE_CANDIDATES: tuple[str, ...] = (
    "config/ai_policies/slide.json",
    "config/slide_ai_policies.json",
)


def _resolve_policy(
    *,
    explicit: Path | None,
    env_var: str | None,
    candidates: Iterable[str],
) -> PolicyResolution:
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

    for candidate in candidates:
        resolved = find_config_path(Path(candidate))
        if resolved:
            return PolicyResolution(resolved, "default")

    return PolicyResolution(None, "missing")


def resolve_template_ai_policy_path(path: Path | None = None) -> PolicyResolution:
    """テンプレート AI ポリシーの探索順を統一する。"""

    return _resolve_policy(
        explicit=path,
        env_var="PPTX_TEMPLATE_AI_POLICY",
        candidates=_TEMPLATE_CANDIDATES,
    )


def resolve_layout_ai_policy_path(path: Path | None = None) -> PolicyResolution:
    """レイアウト AI ポリシーの探索順を統一する。"""

    return _resolve_policy(
        explicit=path,
        env_var="PPTX_LAYOUT_AI_POLICY",
        candidates=_LAYOUT_CANDIDATES,
    )


def resolve_slide_ai_policy_path(path: Path | None = None) -> PolicyResolution:
    """スライド生成 AI ポリシーの探索順を統一する。"""

    return _resolve_policy(
        explicit=path,
        env_var="PPTX_SLIDE_AI_POLICY",
        candidates=_SLIDE_CANDIDATES,
    )


__all__ = [
    "PolicyResolution",
    "resolve_template_ai_policy_path",
    "resolve_layout_ai_policy_path",
    "resolve_slide_ai_policy_path",
]
