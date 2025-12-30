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
from pptx_generator.llm.provider import ProviderResolution


logger = logging.getLogger(__name__)


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
        config = load_openai_chat_config()
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
        edits = _parse_edits(content)
        return EditAIResponse(model=completion.model, edits=edits, raw_text=content)


class AzureOpenAIEditClient(OpenAIEditClient):
    @classmethod
    def from_env(cls) -> "AzureOpenAIEditClient":
        config = load_azure_openai_config()
        import openai

        client = openai.AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        instance = cls(config.deployment_name, config.max_tokens)
        instance._client = client
        instance._model = config.deployment_name
        return instance


class AnthropicEditClient:
    @classmethod
    def from_env(cls) -> "AnthropicEditClient":
        config = load_anthropic_config()
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
        edits = _parse_edits(content)
        return EditAIResponse(model=result.model, edits=edits, raw_text=content)


class AwsClaudeEditClient(AnthropicEditClient):
    @classmethod
    def from_env(cls) -> "AwsClaudeEditClient":
        config = load_aws_claude_config()
        import anthropic

        client = anthropic.Anthropic(
            api_key=config.api_key,
            base_url=config.endpoint,
        )
        instance = cls(config.model, config.max_tokens)
        instance._client = client
        instance._model = config.model
        return instance


def _build_messages(request: EditAIRequest):
    system = """あなたはプレゼン編集アシスタントです。以下の指示に従って JSON を返してください。
- 入力: shape_id と元テキストのリスト、およびスライド情報
- 各要素について、編集指示が含まれているかを判定し、必要なら書き換えた contents を返す
- 出力は JSON 配列のみ: [{"shape_id": number, "edit": true|false, "contents": string}]
- 余計なキーやテキストは出力しないこと
"""
    user = request.prompt
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return messages


def _build_claude_messages(request: EditAIRequest):
    system = """あなたはプレゼン編集アシスタントです。以下の指示に従って JSON を返してください。
- 入力: shape_id と元テキストのリスト、およびスライド情報
- 各要素について、編集指示が含まれているかを判定し、必要なら書き換えた contents を返す
- 出力は JSON 配列のみ: [{"shape_id": number, "edit": true|false, "contents": string}]
- 余計なキーやテキストは出力しないこと
"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": request.prompt},
    ]


def _parse_edits(text: str) -> list[dict[str, object]]:
    try:
        data = json.loads(text)
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

