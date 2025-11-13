"""LLM client for brief generation."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BriefLLMResult:
    text: str
    model: str
    warnings: list[str]
    tokens: dict[str, int]


class BriefLLMClient(Protocol):
    """Interface for brief generation LLM client."""

    def generate(self, prompt: str, *, model_hint: str | None = None) -> BriefLLMResult:
        """Generate a brief JSON string from the given prompt."""


class BriefLLMConfigurationError(RuntimeError):
    """Raised when the client cannot be configured."""


def create_brief_llm_client() -> BriefLLMClient:
    provider = os.getenv("PPTX_LLM_PROVIDER", "mock").strip().lower()
    logger.info("Brief LLM provider resolved: %s", provider)
    if provider in {"", "mock", "mock-local"}:
        return MockBriefLLMClient()
    if provider in {"openai", "openai-api"}:
        return OpenAIBriefLLMClient.from_env()
    if provider in {"azure-openai", "azure"}:
        return AzureOpenAIBriefLLMClient.from_env()
    raise BriefLLMConfigurationError(f"未知の LLM プロバイダーです: {provider}")


class MockBriefLLMClient:
    """Deterministic mock implementation."""

    def generate(self, prompt: str, *, model_hint: str | None = None) -> BriefLLMResult:
        try:
            marker_start = prompt.index("# 入力")
            marker_end = prompt.index("# 出力", marker_start)
            json_block = prompt[marker_start:marker_end]
            start = json_block.index("{")
            end = json_block.rindex("}")
            payload = json.loads(json_block[start : end + 1])
        except (ValueError, json.JSONDecodeError):
            payload = {}
        chapters = payload.get("chapters") or []
        if not isinstance(chapters, list) or not chapters:
            chapters = [{"title": "イントロダクション"}]

        result_chapters: list[dict[str, Any]] = []
        for idx, chapter in enumerate(chapters):
            title = str(chapter.get("title") or f"Chapter {idx+1}")
            narrative = chapter.get("details") or []
            if not isinstance(narrative, list):
                narrative = [str(narrative)]
            intent_tags = chapter.get("intent_tags") or []
            if not isinstance(intent_tags, list):
                intent_tags = [str(intent_tags)]
            story_phase = "introduction"
            if intent_tags:
                story_phase = str(intent_tags[0]).lower()
            result_chapters.append(
                {
                    "title": title,
                    "card_id": f"card-{idx+1}",
                    "story_phase": story_phase,
                    "intent_tags": intent_tags or [story_phase],
                    "message": chapter.get("message") or title,
                    "narrative": [str(line)[:40] for line in narrative[:6]] or [title],
                    "supporting_points": [{"statement": str(line)[:40]} for line in narrative[:3]],
                }
            )
        text = json.dumps({"chapters": result_chapters}, ensure_ascii=False)
        return BriefLLMResult(text=text, model="mock-local", warnings=[], tokens={})


@dataclass
class OpenAIBriefLLMClient:
    """OpenAI Chat Completions based client."""

    client: any
    model: str
    temperature: float
    max_tokens: int

    @classmethod
    def from_env(cls) -> "OpenAIBriefLLMClient":
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            msg = "openai パッケージをインストールしてください (`pip install openai`)."
            raise BriefLLMConfigurationError(msg) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise BriefLLMConfigurationError("OPENAI_API_KEY が設定されていません")
        base_url = os.getenv("OPENAI_BASE_URL")
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "32000"))
        return cls(client=client, model=model, temperature=temperature, max_tokens=max_tokens)

    def generate(self, prompt: str, *, model_hint: str | None = None) -> BriefLLMResult:
        target_model = model_hint or self.model
        messages = [
            {"role": "system", "content": "You are a helpful assistant that returns JSON only."},
            {"role": "user", "content": prompt},
        ]
        kwargs: dict[str, object] = {
            "model": target_model,
            "messages": messages,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        if self.max_tokens > 0:
            kwargs["max_completion_tokens"] = self.max_tokens
        response = self.client.chat.completions.create(**kwargs)  # type: ignore[attr-defined]
        choice = response.choices[0]
        content = getattr(choice.message, "content", "")
        if isinstance(content, list):
            content = "".join(str(part) for part in content)
        usage = getattr(response, "usage", None)
        tokens = {}
        if usage:
            tokens = {
                "prompt": getattr(usage, "prompt_tokens", 0),
                "completion": getattr(usage, "completion_tokens", 0),
                "total": getattr(usage, "total_tokens", 0),
            }
        return BriefLLMResult(text=str(content or ""), model=target_model, warnings=[], tokens=tokens)


@dataclass
class AzureOpenAIBriefLLMClient:
    """Azure OpenAI chat client wrapper."""

    client: any
    deployment: str
    api_version: str
    temperature: float
    max_tokens: int

    @classmethod
    def from_env(cls) -> "AzureOpenAIBriefLLMClient":
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover
            msg = "openai パッケージをインストールしてください (`pip install openai`)."
            raise BriefLLMConfigurationError(msg) from exc

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not all([endpoint, api_key, deployment]):
            raise BriefLLMConfigurationError(
                "AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / AZURE_OPENAI_DEPLOYMENT を設定してください"
            )
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "32000"))
        endpoint = endpoint.rstrip("/")
        lowered = endpoint.lower()
        for suffix in ("/openai/responses", "/openai"):
            if lowered.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                lowered = endpoint.lower()
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )
        return cls(client=client, deployment=deployment, api_version=api_version, temperature=temperature, max_tokens=max_tokens)

    def generate(self, prompt: str, *, model_hint: str | None = None) -> BriefLLMResult:
        target_model = model_hint or self.deployment
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that returns JSON only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
        kwargs: dict[str, object] = {
            "model": target_model,
            "input": messages,
            "temperature": self.temperature,
        }
        if self.max_tokens > 0:
            kwargs["max_output_tokens"] = self.max_tokens
        response = self.client.responses.create(**kwargs)  # type: ignore[attr-defined]
        output = getattr(response, "output", []) or []
        texts: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if not content:
                continue
            for entry in content:
                text_value: str | None = None
                if isinstance(entry, dict):
                    text_value = entry.get("text")  # type: ignore[assignment]
                else:
                    text_value = getattr(entry, "text", None)
                if text_value:
                    texts.append(str(text_value))
        if not texts:
            output_text = getattr(response, "output_text", None)
            if output_text:
                if isinstance(output_text, list):  # Azure SDK may return list[str]
                    texts.extend(str(segment) for segment in output_text if segment)
                elif isinstance(output_text, str):
                    texts.append(output_text)

        tokens = {}
        usage = getattr(response, "usage", None)
        if usage:
            tokens = {
                "prompt": getattr(usage, "prompt_tokens", 0),
                "completion": getattr(usage, "completion_tokens", 0),
                "total": getattr(usage, "total_tokens", 0),
            }
        return BriefLLMResult(text="".join(texts), model=self.deployment, warnings=[], tokens=tokens)
