"""LLM client for prepare generation."""

from __future__ import annotations

import json
import math
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from pptx_generator.llm import resolve_llm_provider


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PrepareLLMResult:
    text: str
    model: str
    warnings: list[str]
    tokens: dict[str, int]


class PrepareLLMClient(Protocol):
    """Interface for prepare generation LLM client."""

    def generate(self, prompt: str, *, model_hint: str | None = None) -> PrepareLLMResult:
        """Generate a prepare JSON string from the given prompt."""


class PrepareLLMConfigurationError(RuntimeError):
    """Raised when the client cannot be configured."""


def create_prepare_llm_client() -> PrepareLLMClient:
    resolution = resolve_llm_provider()
    logger.info(
        "Prepare LLM provider resolved: %s (source=%s)",
        resolution.provider,
        resolution.source,
    )

    factories: dict[str, Callable[[], PrepareLLMClient]] = {
        "mock": MockPrepareLLMClient,
        "openai": OpenAIPrepareLLMClient.from_env,
        "azure-openai": AzureOpenAIPrepareLLMClient.from_env,
    }

    factory = factories.get(resolution.provider)
    if factory is None:
        raise PrepareLLMConfigurationError(f"未知の LLM プロバイダーです: {resolution.provider}")

    return factory()


class MockPrepareLLMClient:
    """Deterministic mock implementation."""

    def generate(self, prompt: str, *, model_hint: str | None = None) -> PrepareLLMResult:
        try:
            marker_start = prompt.index("# 入力")
            marker_end = prompt.index("# 出力", marker_start)
            json_block = prompt[marker_start:marker_end]
            start = json_block.index("{")
            end = json_block.rindex("}")
            payload = json.loads(json_block[start : end + 1])
        except (ValueError, json.JSONDecodeError):
            payload = {}
        slot_specs = payload.get("slot_specs")
        if isinstance(slot_specs, list) and slot_specs:
            slots_result: list[dict[str, Any]] = []
            for spec in slot_specs:
                slot_id = str(spec.get("slot_id"))
                context = spec.get("context") or ""
                lines = [line.strip() for line in str(context).splitlines() if line.strip()]
                base_line = lines[0] if lines else slot_id.replace(".", " ").title()
                slots_result.append(
                    {
                        "slot_id": slot_id,
                        "headline": base_line[:60],
                        "subtitle": None,
                        "body": [
                            {
                                "type": "paragraph",
                                "text": base_line[:80],
                            }
                        ],
                        "notes": [],
                    }
                )
            text = json.dumps({"slots": slots_result}, ensure_ascii=False)
        else:
            constraints = payload.get("constraints") or {}
            max_chapters = constraints.get("max_chapters")
            if isinstance(max_chapters, int) and max_chapters > 0:
                chapter_count = max_chapters
            else:
                chapter_count = 4

            raw_context = payload.get("raw_context") or {}
            text_source = raw_context.get("content") or ""
            lines = [line.strip() for line in text_source.splitlines() if line.strip()]
            bullets = [line[2:].strip() for line in lines if line.startswith("- ") and line[2:].strip()]
            if not bullets:
                bullets = lines
            if not bullets:
                bullets = [f"セクション {idx + 1}" for idx in range(chapter_count)]

            # 保証: bullets が chapter_count 以上になるよう補完
            while len(bullets) < chapter_count:
                bullets.append(bullets[-1])

            story_framework = ["introduction", "problem", "solution", "impact", "next"]

            chunk_size = max(1, math.ceil(len(bullets) / chapter_count))
            result_chapters: list[dict[str, Any]] = []
            for idx in range(chapter_count):
                start_index = idx * chunk_size
                segment = bullets[start_index : start_index + chunk_size]
                if not segment:
                    segment = [bullets[min(idx, len(bullets) - 1)]]

                story_phase = story_framework[idx % len(story_framework)].lower()
                card_id = f"{story_phase}-{idx + 1}"

                title = segment[0][:60] if segment[0] else f"Chapter {idx + 1}"
                narrative = [entry[:80] for entry in segment]
                body_blocks = [
                    {
                        "type": "paragraph",
                        "text": entry,
                    }
                    for entry in narrative
                ]
                notes = [
                    {
                        "type": "rationale",
                        "text": entry,
                    }
                    for entry in narrative
                ]

                result_chapters.append(
                    {
                        "title": title or f"Chapter {idx + 1}",
                        "card_id": card_id,
                        "story_phase": story_phase,
                        "intent_tags": [story_phase],
                        "headline": title or f"Chapter {idx + 1}",
                        "body": body_blocks,
                        "notes": notes,
                    }
                )

            text = json.dumps({"chapters": result_chapters}, ensure_ascii=False)
        return PrepareLLMResult(text=text, model="mock-local", warnings=[], tokens={})


@dataclass
class OpenAIPrepareLLMClient:
    """OpenAI Chat Completions based client."""

    client: any
    model: str
    temperature: float
    max_tokens: int

    @classmethod
    def from_env(cls) -> "OpenAIPrepareLLMClient":
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            msg = "openai パッケージをインストールしてください (`pip install openai`)."
            raise PrepareLLMConfigurationError(msg) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise PrepareLLMConfigurationError("OPENAI_API_KEY が設定されていません")
        base_url = os.getenv("OPENAI_BASE_URL")
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "32000"))
        return cls(client=client, model=model, temperature=temperature, max_tokens=max_tokens)

    def generate(self, prompt: str, *, model_hint: str | None = None) -> PrepareLLMResult:
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
        return PrepareLLMResult(text=str(content or ""), model=target_model, warnings=[], tokens=tokens)


@dataclass
class AzureOpenAIPrepareLLMClient:
    """Azure OpenAI chat client wrapper."""

    client: any
    deployment: str
    api_version: str
    temperature: float
    max_tokens: int

    @classmethod
    def from_env(cls) -> "AzureOpenAIPrepareLLMClient":
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover
            msg = "openai パッケージをインストールしてください (`pip install openai`)."
            raise PrepareLLMConfigurationError(msg) from exc

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not all([endpoint, api_key, deployment]):
            raise PrepareLLMConfigurationError(
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

    def generate(self, prompt: str, *, model_hint: str | None = None) -> PrepareLLMResult:
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
        return PrepareLLMResult(text="".join(texts), model=self.deployment, warnings=[], tokens=tokens)
