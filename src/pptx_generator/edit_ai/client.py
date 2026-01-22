from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Iterable, Protocol

from pptx_generator.llm import (
    log_provider_resolution,
    resolve_llm_provider,
    load_anthropic_config,
    load_azure_openai_config,
    load_aws_claude_config,
    load_openai_chat_config,
)
from pptx_generator.llm.json_utils import extract_json_value
from pptx_generator.llm.provider import ProviderResolution


logger = logging.getLogger(__name__)
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20240620"
DEFAULT_AWS_CLAUDE_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"
EDIT_SYSTEM_PROMPT = """あなたはプレゼン編集アシスタントです。以下の指示に従って JSON を返してください。
- 入力: shape_id と元テキストのリスト、およびスライド情報
- 各要素について、編集指示が含まれているかを判定し、必要なら書き換えた contents を返す
- 出力は JSON 配列のみ: [{"shape_id": number, "edit": true|false, "contents": string}]
- 余計なキーやテキストは出力しないこと
- 箇条書きは元の構造をできるだけ保つ（改行・リスト記号を維持）
- 固有名詞は改変しない
"""


@dataclass(slots=True)
class EditAIRequest:
    """Stage5 指示適用用の LLM リクエスト。"""

    prompt: str
    shape_contexts: list[dict[str, object]]
    model: str | None = None
    max_tokens: int | None = None


@dataclass(slots=True)
class EditAIResponse:
    """LLM からの応答。"""

    model: str
    edits: list[dict[str, object]] = field(default_factory=list)
    raw_text: str | None = None


class EditAIClient(Protocol):
    def rewrite(self, request: EditAIRequest) -> EditAIResponse:
        """指示検出とテキスト変換を行う。"""


class EditAIClientConfigurationError(RuntimeError):
    pass


class EditAIClientExecutionError(RuntimeError):
    pass


class EditAIResponseFormatError(RuntimeError):
    pass


def create_edit_ai_client() -> EditAIClient:
    resolution = resolve_llm_provider()
    log_provider_resolution(logger, component="edit_ai", resolution=resolution)

    factories = {
        "mock": MockEditAIClient,
        "openai": OpenAIEditClient.from_env,
        "azure-openai": AzureOpenAIEditClient.from_env,
        "anthropic": AnthropicEditClient.from_env,
        "aws-claude": AwsClaudeEditClient.from_env,
    }

    factory = factories.get(resolution.provider)
    if factory is None:
        raise EditAIClientConfigurationError(
            f"未知の edit_ai プロバイダが指定されました: {resolution.provider}"
        )
    return factory()


class MockEditAIClient:
    def __init__(self) -> None:
        self.model = "mock-edit"

    def rewrite(self, request: EditAIRequest) -> EditAIResponse:
        edits: list[dict[str, object]] = []
        for shape in request.shape_contexts:
            edits.append(
                {
                    "shape_id": shape.get("shape_id"),
                    "edit": False,
                    "contents": shape.get("text", ""),
                }
            )
        return EditAIResponse(model=self.model, edits=edits, raw_text=json.dumps(edits))


class OpenAIEditClient:
    @classmethod
    def from_env(cls) -> "OpenAIEditClient":
        config = load_openai_chat_config(
            default_model=DEFAULT_OPENAI_MODEL,
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=EditAIClientConfigurationError,
        )
        return cls(config.model, config.max_tokens)

    def __init__(self, model: str, max_tokens: int | None):
        import openai

        self._client = openai.OpenAI()
        self._model = model
        self._max_tokens = max_tokens

    def rewrite(self, request: EditAIRequest) -> EditAIResponse:
        messages = _build_messages(request)
        try:
            completion = self._client.chat.completions.create(
                model=request.model or self._model,
                messages=messages,
                max_tokens=request.max_tokens or self._max_tokens,
                temperature=0,
            )
        except Exception as exc:  # noqa: BLE001
            raise EditAIClientExecutionError(str(exc)) from exc
        content = completion.choices[0].message.content or ""
        logger.debug("OpenAI edit raw response: %s", content)
        edits = _parse_edits(content)
        return EditAIResponse(model=completion.model, edits=edits, raw_text=content)


class AzureOpenAIEditClient(OpenAIEditClient):
    @classmethod
    def from_env(cls) -> "AzureOpenAIEditClient":
        config = load_azure_openai_config(
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            default_api_version=DEFAULT_AZURE_API_VERSION,
            error_cls=EditAIClientConfigurationError,
        )
        import openai

        client = openai.AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        instance = cls(config.deployment, config.max_tokens)
        instance._client = client
        instance._model = config.deployment
        return instance

    def rewrite(self, request: EditAIRequest) -> EditAIResponse:
        messages = _build_messages(request)
        kwargs: dict[str, object] = {
            "model": request.model or self._model,
            "messages": messages,
            "temperature": 0,
        }
        if (request.max_tokens or self._max_tokens) and (request.max_tokens or self._max_tokens) > 0:
            kwargs["max_completion_tokens"] = request.max_tokens or self._max_tokens
        try:
            completion = self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise EditAIClientExecutionError(str(exc)) from exc
        content = completion.choices[0].message.content or ""
        logger.debug("Azure OpenAI edit raw response: %s", content)
        edits = _parse_edits(content)
        return EditAIResponse(model=completion.model, edits=edits, raw_text=content)


class AnthropicEditClient:
    @classmethod
    def from_env(cls) -> "AnthropicEditClient":
        config = load_anthropic_config(
            default_model=DEFAULT_ANTHROPIC_MODEL,
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=EditAIClientConfigurationError,
        )
        return cls(config.model, config.max_tokens)

    def __init__(self, model: str, max_tokens: int | None):
        import anthropic

        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens or 2048

    def rewrite(self, request: EditAIRequest) -> EditAIResponse:
        from anthropic.types import MessageParam

        messages: list[MessageParam] = _build_claude_messages(request)
        try:
            result = self._client.messages.create(
                model=request.model or self._model,
                max_tokens=request.max_tokens or self._max_tokens,
                temperature=0,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            raise EditAIClientExecutionError(str(exc)) from exc
        content = "".join(block.text for block in result.content if getattr(block, "text", None))
        logger.debug("Anthropic edit raw response: %s", content)
        edits = _parse_edits(content)
        return EditAIResponse(model=result.model, edits=edits, raw_text=content)


class AwsClaudeEditClient:
    @classmethod
    def from_env(cls) -> "AwsClaudeEditClient":
        import boto3
        from botocore.exceptions import NoCredentialsError

        config = load_aws_claude_config(
            default_model_id=DEFAULT_AWS_CLAUDE_MODEL,
            default_temperature=DEFAULT_TEMPERATURE,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=EditAIClientConfigurationError,
        )

        session_kwargs: dict[str, object] = {}
        if config.profile:
            session_kwargs["profile_name"] = config.profile
        if config.region:
            session_kwargs["region_name"] = config.region
        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise EditAIClientConfigurationError(
                "AWS 認証情報が見つかりません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定するか、`aws configure` で設定してください。"
            )

        client_kwargs: dict[str, object] = {}
        if config.region:
            client_kwargs["region_name"] = config.region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise EditAIClientConfigurationError(
                "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
            ) from exc

        return cls(
            runtime_client,
            model_id=config.model_id,
            max_tokens=config.max_tokens,
            inference_profile_arn=config.inference_profile_arn,
            temperature=config.temperature,
        )

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
        self._max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self._inference_profile_arn = inference_profile_arn
        self._temperature = temperature

    def _resolve_model_id(self, override: str | None) -> str:
        if override and override.strip() and override != "mock-local":
            return override
        return self._model_id

    def _invoke_bedrock(self, *, model_id: str, payload: dict[str, object]) -> str:
        invoke_kwargs = {
            "modelId": model_id,
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
        data = json.loads(body_text)
        text_parts = [item.get("text", "") for item in data.get("content", []) if isinstance(item, dict)]
        return "\n".join(part.strip() for part in text_parts if isinstance(part, str) and part.strip())

    def rewrite(self, request: EditAIRequest) -> EditAIResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": self._temperature,
            "system": EDIT_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": request.prompt,
                        }
                    ],
                }
            ],
        }
        model_id = self._resolve_model_id(request.model)
        try:
            text = self._invoke_bedrock(model_id=model_id, payload=payload)
        except Exception as exc:  # noqa: BLE001
            raise EditAIClientExecutionError(str(exc)) from exc
        logger.debug("AWS Claude edit raw response: %s", text)
        edits = _parse_edits(text)
        return EditAIResponse(model=model_id, edits=edits, raw_text=text)


def _build_messages(request: EditAIRequest):
    return [
        {"role": "system", "content": EDIT_SYSTEM_PROMPT},
        {"role": "user", "content": request.prompt},
    ]


def _build_claude_messages(request: EditAIRequest):
    return [
        {"role": "system", "content": EDIT_SYSTEM_PROMPT},
        {"role": "user", "content": request.prompt},
    ]


def _parse_edits(text: str) -> list[dict[str, object]]:
    try:
        data = extract_json_value(text)
    except Exception as exc:  # noqa: BLE001
        raise EditAIResponseFormatError("LLM 応答を JSON として解釈できません") from exc
    if isinstance(data, dict) and "edits" in data:
        data = data.get("edits", [])
    if not isinstance(data, list):
        raise EditAIResponseFormatError("LLM 応答は配列または {edits: [...]} 形式である必要があります")
    cleaned: list[dict[str, object]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "shape_id" not in item or "contents" not in item:
            continue
        cleaned.append(
            {
                "shape_id": item.get("shape_id"),
                "edit": bool(item.get("edit", True)),
                "contents": str(item.get("contents", "")),
            }
        )
    return cleaned
