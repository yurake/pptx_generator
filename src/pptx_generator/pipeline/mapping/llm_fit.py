"""マッピング stage の本文フィット用 LLM クライアント。"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol

from pptx_generator.llm import (
    load_anthropic_config,
    load_aws_claude_config,
    load_azure_openai_config,
    load_openai_chat_config,
    log_provider_resolution,
    resolve_llm_provider,
)
from pptx_generator.llm.json_utils import extract_json_object

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20240620"
DEFAULT_AWS_CLAUDE_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"

SYSTEM_PROMPT = """あなたはプレゼン資料の本文を調整する編集者です。
次のルールを必ず守って JSON のみを返してください。
- 出力は JSON オブジェクトのみ (コードフェンス不可)
- keys: body, subtitle, note のみを返す
- body は文字列配列で返す
- max_lines / max_chars を超えないように本文を再編集する
- 元の意味・順序・重要語を保つ
- 固有名詞や数値を改変しない
"""


@dataclass(slots=True)
class MappingTextFitRequest:
    slide_id: str
    layout_id: str | None
    max_lines: int | None
    max_chars: int | None
    body: list[str]
    subtitle: str | None = None
    note: str | None = None


@dataclass(slots=True)
class MappingTextFitResponse:
    model: str
    body: list[str]
    subtitle: str | None = None
    note: str | None = None
    raw_text: str | None = None


class MappingTextFitClient(Protocol):
    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        """本文を制約内に収める。"""


class MappingTextFitClientConfigurationError(RuntimeError):
    """LLM 設定に関するエラー。"""


class MappingTextFitClientExecutionError(RuntimeError):
    """LLM 実行時のエラー。"""


class MappingTextFitResponseFormatError(RuntimeError):
    """LLM 応答が期待形式ではない場合のエラー。"""


def create_mapping_text_fit_client() -> MappingTextFitClient:
    resolution = resolve_llm_provider()
    log_provider_resolution(logger, component="mapping_text_fit", resolution=resolution)

    factories: dict[str, type[MappingTextFitClient]] = {
        "mock": MockMappingTextFitClient,
        "openai": OpenAITextFitClient,
        "azure-openai": AzureOpenAITextFitClient,
        "anthropic": AnthropicTextFitClient,
        "aws-claude": AwsClaudeTextFitClient,
    }
    factory = factories.get(resolution.provider)
    if factory is None:
        raise MappingTextFitClientConfigurationError(
            f"未知の LLM プロバイダが指定されました: {resolution.provider}"
        )
    if hasattr(factory, "from_env"):
        return getattr(factory, "from_env")()
    return factory()  # type: ignore[call-arg]


class MockMappingTextFitClient:
    def __init__(self) -> None:
        self._model = "mock-mapping-text-fit"

    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        body = _fit_mock_body(request.body, request.max_lines, request.max_chars)
        return MappingTextFitResponse(
            model=self._model,
            body=body,
            subtitle=request.subtitle,
            note=request.note,
            raw_text=json.dumps({"body": body, "subtitle": request.subtitle, "note": request.note}, ensure_ascii=False),
        )


class OpenAITextFitClient:
    def __init__(self, client, *, model: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "OpenAITextFitClient":
        from openai import OpenAI

        config = load_openai_chat_config(
            default_model=DEFAULT_OPENAI_MODEL,
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=MappingTextFitClientConfigurationError,
        )
        client = OpenAI(api_key=config.api_key, base_url=config.base_url) if config.base_url else OpenAI(api_key=config.api_key)
        return cls(client, model=config.model, temperature=config.temperature, max_tokens=config.max_tokens)

    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputText, ResponseOutputRefusal

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        kwargs: dict[str, object] = {
            "input": messages,
            "model": self._model,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens

        try:
            response = self._client.responses.create(**kwargs)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise MappingTextFitClientExecutionError(str(exc)) from exc

        text_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):  # pragma: no cover - refusal only
                        logger.info("OpenAI mapping text fit refusal: %s", content.refusal)

        raw_text = "\n".join(segment.strip() for segment in text_segments if segment and segment.strip())
        if not raw_text:
            raise MappingTextFitResponseFormatError("OpenAI 応答が空でした")
        return _parse_text_fit_response(raw_text, model=self._model)


class AzureOpenAITextFitClient:
    def __init__(self, client, *, deployment: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._deployment = deployment
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "AzureOpenAITextFitClient":
        from openai import AzureOpenAI

        config = load_azure_openai_config(
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            default_api_version=DEFAULT_AZURE_API_VERSION,
            error_cls=MappingTextFitClientConfigurationError,
        )
        client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        return cls(client, deployment=config.deployment, temperature=config.temperature, max_tokens=config.max_tokens)

    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputText, ResponseOutputRefusal

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        kwargs: dict[str, object] = {
            "model": self._deployment,
            "input": messages,
            "temperature": self._temperature,
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens

        try:
            response = self._client.responses.create(**kwargs)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise MappingTextFitClientExecutionError(str(exc)) from exc

        text_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):  # pragma: no cover - refusal only
                        logger.info("Azure OpenAI mapping text fit refusal: %s", content.refusal)

        raw_text = "\n".join(segment.strip() for segment in text_segments if segment and segment.strip())
        if not raw_text:
            raise MappingTextFitResponseFormatError("Azure OpenAI 応答が空でした")
        return _parse_text_fit_response(raw_text, model=f"azure-openai:{self._deployment}")


class AnthropicTextFitClient:
    def __init__(self, client, *, model: str, max_tokens: int, temperature: float) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    @classmethod
    def from_env(cls) -> "AnthropicTextFitClient":
        import anthropic

        config = load_anthropic_config(
            default_model=DEFAULT_ANTHROPIC_MODEL,
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=MappingTextFitClientConfigurationError,
        )
        client = anthropic.Anthropic(api_key=config.api_key)
        return cls(client, model=config.model, max_tokens=config.max_tokens, temperature=config.temperature)

    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        model_name = self._model or ""
        start = time.perf_counter()
        try:
            response = self._client.messages.create(  # type: ignore[attr-defined]
                model=model_name,
                system=SYSTEM_PROMPT,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": _build_user_prompt(request),
                            }
                        ],
                    }
                ],
            )
        except Exception as exc:  # pragma: no cover - API failure
            logger.error("Anthropic mapping text fit failed: model=%s error=%s", model_name, exc)
            raise MappingTextFitClientExecutionError(str(exc)) from exc

        latency_ms = (time.perf_counter() - start) * 1000
        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        raw_text = "\n".join(part.strip() for part in text_parts if part.strip())
        if not raw_text:
            raise MappingTextFitResponseFormatError("Anthropic 応答が空でした")
        logger.info(
            "mapping text fit done: provider=anthropic model=%s latency_ms=%.1f",
            model_name,
            latency_ms,
        )
        return _parse_text_fit_response(raw_text, model=f"anthropic:{model_name}")


class AwsClaudeTextFitClient:
    def __init__(
        self,
        runtime_client,
        *,
        model_id: str,
        max_tokens: int,
        inference_profile_arn: str | None,
        temperature: float,
    ) -> None:
        self._client = runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._inference_profile_arn = inference_profile_arn
        self._temperature = temperature

    @classmethod
    def from_env(cls) -> "AwsClaudeTextFitClient":
        import boto3
        from botocore.exceptions import NoCredentialsError

        config = load_aws_claude_config(
            default_model_id=DEFAULT_AWS_CLAUDE_MODEL,
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=MappingTextFitClientConfigurationError,
        )

        session_kwargs: dict[str, Any] = {}
        if config.profile:
            session_kwargs["profile_name"] = config.profile
        if config.region:
            session_kwargs["region_name"] = config.region

        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise MappingTextFitClientConfigurationError(
                "AWS 認証情報が見つかりません。AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY を設定してください。"
            )

        client_kwargs: dict[str, Any] = {}
        if config.region:
            client_kwargs["region_name"] = config.region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise MappingTextFitClientConfigurationError(
                "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
            ) from exc

        return cls(
            runtime_client,
            model_id=config.model_id,
            max_tokens=config.max_tokens,
            inference_profile_arn=config.inference_profile_arn,
            temperature=config.temperature,
        )

    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": _build_user_prompt(request),
                        }
                    ],
                }
            ],
        }
        invoke_kwargs: dict[str, Any] = {
            "modelId": self._model_id,
            "body": json.dumps(payload),
            "contentType": "application/json",
            "accept": "application/json",
        }
        if self._inference_profile_arn:
            invoke_kwargs["inferenceProfileArn"] = self._inference_profile_arn

        response = self._client.invoke_model(**invoke_kwargs)
        body = response.get("body")
        body_text = body.read() if hasattr(body, "read") else body
        if isinstance(body_text, (bytes, bytearray)):
            body_text = body_text.decode("utf-8")
        try:
            data = json.loads(body_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise MappingTextFitClientExecutionError(f"AWS Claude 応答の解析に失敗しました: {exc}") from exc

        text_parts = [
            item.get("text", "") for item in data.get("content", []) if isinstance(item, dict)
        ]
        raw_text = "\n".join(part.strip() for part in text_parts if isinstance(part, str) and part.strip())
        if not raw_text:
            raise MappingTextFitResponseFormatError("AWS Claude 応答が空でした")
        return _parse_text_fit_response(raw_text, model=f"aws-claude:{self._model_id}")


def _build_user_prompt(request: MappingTextFitRequest) -> str:
    payload = {
        "constraints": {
            "max_lines": request.max_lines,
            "max_chars": request.max_chars,
        },
        "elements": {
            "body": request.body,
            "subtitle": request.subtitle,
            "note": request.note,
        },
        "slide_id": request.slide_id,
        "layout_id": request.layout_id,
    }
    return (
        "入力:\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n\n"
        + "出力は JSON のみ。body を制約内に調整してください。"
    )


def _parse_text_fit_response(raw_text: str, *, model: str) -> MappingTextFitResponse:
    try:
        data = extract_json_object(raw_text)
    except json.JSONDecodeError as exc:
        raise MappingTextFitResponseFormatError(f"JSON 解析に失敗しました: {exc}") from exc

    body = _normalize_body(data.get("body"))
    subtitle = _normalize_optional_text(data.get("subtitle"))
    note = _normalize_optional_text(data.get("note"))
    return MappingTextFitResponse(
        model=model,
        body=body,
        subtitle=subtitle,
        note=note,
        raw_text=raw_text,
    )


def _normalize_body(value: Any) -> list[str]:
    if value is None:
        raise MappingTextFitResponseFormatError("body が含まれていません")
    if isinstance(value, list):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []
        return [trimmed]
    return [str(value).strip()]


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    trimmed = str(value).strip()
    return trimmed if trimmed else None


def _fit_mock_body(body: list[str], max_lines: int | None, max_chars: int | None) -> list[str]:
    lines = list(body)
    trimmed = False
    if max_lines is not None and max_lines >= 0:
        if len(lines) > max_lines:
            trimmed = True
            lines = lines[:max_lines]
    if max_chars is None or max_chars < 0:
        if trimmed and lines:
            lines[-1] = _append_ellipsis(lines[-1])
        return lines

    while lines and _count_chars(lines) > max_chars:
        if len(lines) == 1:
            lines[0] = _truncate_line(lines[0], max_chars)
            trimmed = True
            break
        lines.pop()
        trimmed = True
    if trimmed and lines:
        lines[-1] = _append_ellipsis(lines[-1])
    return lines


def _truncate_line(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    trimmed = text[:max_chars].rstrip()
    return _append_ellipsis(trimmed) if trimmed else ""


def _append_ellipsis(text: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return "..."
    if stripped.endswith("..."):
        return stripped
    return f"{stripped}..."


def _count_chars(lines: list[str]) -> int:
    return sum(len(line) for line in lines)
