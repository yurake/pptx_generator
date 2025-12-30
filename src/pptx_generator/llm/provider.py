"""LLM プロバイダ解決ロジック。"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Mapping


PROVIDER_ALIASES: dict[str, str] = {
    "": "mock",
    "mock": "mock",
    "mock-local": "mock",
    "openai": "openai",
    "openai-api": "openai",
    "azure": "azure-openai",
    "azure-openai": "azure-openai",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "aws-claude": "aws-claude",
    "bedrock": "aws-claude",
}


@dataclass(frozen=True)
class ProviderResolution:
    """LLM プロバイダ解決結果。"""

    provider: str
    source: str
    raw_value: str | None

    @property
    def is_default(self) -> bool:
        return self.source == "default"


def resolve_llm_provider(
    *,
    primary_env: str = "PPTX_LLM_PROVIDER",
    fallback_env: str | None = None,
    default: str = "mock",
    aliases: Mapping[str, str] | None = None,
) -> ProviderResolution:
    """環境変数から LLM プロバイダを解決する。"""

    alias_map = {key.lower(): value for key, value in PROVIDER_ALIASES.items()}
    if aliases:
        alias_map.update({key.lower(): value for key, value in aliases.items()})

    default_key = default.strip().lower() or "mock"
    default_provider = alias_map.get(default_key, default_key)

    for env_name in _iter_env_names(primary_env, fallback_env):
        raw_value = os.getenv(env_name)
        if raw_value is None:
            continue
        trimmed = raw_value.strip()
        if not trimmed:
            return ProviderResolution(default_provider, env_name, raw_value)
        provider = alias_map.get(trimmed.lower(), trimmed.lower())
        return ProviderResolution(provider, env_name, raw_value)

    return ProviderResolution(default_provider, "default", None)


def _iter_env_names(primary_env: str, fallback_env: str | None) -> tuple[str, ...]:
    names: list[str] = []
    if primary_env:
        names.append(primary_env)
    if fallback_env and fallback_env not in names:
        names.append(fallback_env)
    return tuple(names)


def log_provider_resolution(
    logger: logging.Logger,
    *,
    component: str,
    resolution: ProviderResolution,
    **extra_fields: object,
) -> None:
    """プロバイダ解決結果を共通フォーマットでログ出力する。"""

    payload = {
        "component": component,
        "provider": resolution.provider,
        "source": resolution.source,
        **extra_fields,
    }
    formatted = " ".join(f"{key}={value}" for key, value in payload.items())
    logger.info("LLM provider resolved: %s", formatted)
