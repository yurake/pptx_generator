"""LLM プロバイダ向けの環境変数共通ローダー。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Type, TypeVar

TError = TypeVar("TError", bound=Exception)


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    base_url: str | None
    model: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint: str
    api_key: str
    deployment: str
    api_version: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class AnthropicConfig:
    api_key: str
    model: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class AwsClaudeConfig:
    model_id: str
    max_tokens: int
    temperature: float
    region: str | None
    profile: str | None
    inference_profile_arn: str | None


def load_openai_chat_config(
    *,
    default_model: str,
    default_temperature: float,
    default_max_tokens: int,
    error_cls: Type[TError],
) -> OpenAIConfig:
    api_key = _require_env(
        "OPENAI_API_KEY",
        error_cls,
        "OPENAI_API_KEY が設定されていません",
    )
    base_url = os.getenv("OPENAI_BASE_URL") or None
    model = os.getenv("OPENAI_MODEL", default_model)
    temperature = _parse_float(
        os.getenv("OPENAI_TEMPERATURE"),
        default_temperature,
        env_name="OPENAI_TEMPERATURE",
        error_cls=error_cls,
    )
    max_tokens = _parse_int(
        os.getenv("OPENAI_MAX_TOKENS"),
        default_max_tokens,
        env_name="OPENAI_MAX_TOKENS",
        error_cls=error_cls,
    )
    return OpenAIConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def load_azure_openai_config(
    *,
    default_temperature: float,
    default_max_tokens: int,
    default_api_version: str,
    error_cls: Type[TError],
) -> AzureOpenAIConfig:
    raw_endpoint = _require_env(
        "AZURE_OPENAI_ENDPOINT",
        error_cls,
        "AZURE_OPENAI_ENDPOINT を設定してください",
    )
    api_key = _require_env(
        "AZURE_OPENAI_API_KEY",
        error_cls,
        "AZURE_OPENAI_API_KEY を設定してください",
    )
    deployment = _require_env(
        "AZURE_OPENAI_DEPLOYMENT",
        error_cls,
        "AZURE_OPENAI_DEPLOYMENT が設定されていません",
    )
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", default_api_version)
    temperature = _parse_float(
        os.getenv("AZURE_OPENAI_TEMPERATURE"),
        default_temperature,
        env_name="AZURE_OPENAI_TEMPERATURE",
        error_cls=error_cls,
    )
    max_tokens = _parse_int(
        os.getenv("AZURE_OPENAI_MAX_TOKENS"),
        default_max_tokens,
        env_name="AZURE_OPENAI_MAX_TOKENS",
        error_cls=error_cls,
    )
    endpoint = _normalize_azure_endpoint(raw_endpoint)
    return AzureOpenAIConfig(
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
        api_version=api_version,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def load_anthropic_config(
    *,
    default_model: str,
    default_temperature: float,
    default_max_tokens: int,
    error_cls: Type[TError],
) -> AnthropicConfig:
    api_key = _require_env(
        "ANTHROPIC_API_KEY",
        error_cls,
        "ANTHROPIC_API_KEY が設定されていません",
    )
    model = os.getenv("ANTHROPIC_MODEL", default_model)
    temperature = _parse_float(
        os.getenv("ANTHROPIC_TEMPERATURE"),
        default_temperature,
        env_name="ANTHROPIC_TEMPERATURE",
        error_cls=error_cls,
    )
    max_tokens = _parse_int(
        os.getenv("ANTHROPIC_MAX_TOKENS"),
        default_max_tokens,
        env_name="ANTHROPIC_MAX_TOKENS",
        error_cls=error_cls,
    )
    return AnthropicConfig(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def load_aws_claude_config(
    *,
    default_model_id: str,
    default_temperature: float,
    default_max_tokens: int,
    error_cls: Type[TError],
) -> AwsClaudeConfig:
    model_id = os.getenv("AWS_CLAUDE_MODEL_ID", default_model_id)
    inference_profile_arn = os.getenv("AWS_CLAUDE_INFERENCE_PROFILE_ARN")
    region = os.getenv("AWS_REGION")
    profile = os.getenv("AWS_PROFILE")
    temperature = _parse_float(
        os.getenv("AWS_CLAUDE_TEMPERATURE"),
        default_temperature,
        env_name="AWS_CLAUDE_TEMPERATURE",
        error_cls=error_cls,
    )
    max_tokens = _parse_int(
        os.getenv("AWS_CLAUDE_MAX_TOKENS"),
        default_max_tokens,
        env_name="AWS_CLAUDE_MAX_TOKENS",
        error_cls=error_cls,
    )
    return AwsClaudeConfig(
        model_id=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        region=region,
        profile=profile,
        inference_profile_arn=inference_profile_arn,
    )


def _require_env(name: str, error_cls: Type[TError], message: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise error_cls(message)
    return value


def _parse_int(value: str | None, default: int, *, env_name: str, error_cls: Type[TError]) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise error_cls(f"{env_name} must be an integer") from exc


def _parse_float(
    value: str | None, default: float, *, env_name: str, error_cls: Type[TError]
) -> float:
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise error_cls(f"{env_name} must be a float") from exc


def _normalize_azure_endpoint(raw: str) -> str:
    return raw.rstrip("/")
