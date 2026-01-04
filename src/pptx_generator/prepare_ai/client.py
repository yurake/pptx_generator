"""LLM client for prepare generation."""

from __future__ import annotations

import json
import math
import logging
from dataclasses import dataclass
from typing import Any, Callable, Protocol
import time

from pptx_generator.llm import (
    log_provider_resolution,
    resolve_llm_provider,
    load_openai_chat_config,
    load_azure_openai_config,
    load_anthropic_config,
    load_aws_claude_config,
)


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
    log_provider_resolution(logger, component="prepare_ai", resolution=resolution)

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
        from openai import OpenAI

        config = load_openai_chat_config(
            default_model="gpt-5-mini",
            default_temperature=0.3,
            default_max_tokens=32000,
            error_cls=PrepareLLMConfigurationError,
        )
        client = OpenAI(api_key=config.api_key, base_url=config.base_url) if config.base_url else OpenAI(api_key=config.api_key)
        return cls(client=client, model=config.model, temperature=config.temperature, max_tokens=config.max_tokens)

    def generate(self, prompt: str, *, model_hint: str | None = None) -> PrepareLLMResult:
        target_model = model_hint or self.model
        start = time.perf_counter()
        logger.info(
            "prepare_ai call start: provider=openai model=%s",
            target_model,
        )
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
        latency_ms = (time.perf_counter() - start) * 1000
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
        logger.debug("prepare_ai openai raw response: %s", response)
        logger.info(
            "prepare_ai call done: provider=openai model=%s latency_ms=%.1f finish_reason=%s",
            target_model,
            latency_ms,
            getattr(choice, "finish_reason", None),
        )
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
        from openai import AzureOpenAI

        config = load_azure_openai_config(
            default_temperature=0.3,
            default_max_tokens=32000,
            default_api_version="2024-02-15-preview",
            error_cls=PrepareLLMConfigurationError,
        )
        client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        return cls(
            client=client,
            deployment=config.deployment,
            api_version=config.api_version,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def generate(self, prompt: str, *, model_hint: str | None = None) -> PrepareLLMResult:
        target_model = model_hint or self.deployment
        start = time.perf_counter()
        logger.info(
            "prepare_ai call start: provider=azure model=%s",
            target_model,
        )
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
        latency_ms = (time.perf_counter() - start) * 1000
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
        logger.debug("prepare_ai azure raw response: %s", response)
        logger.info(
            "prepare_ai call done: provider=azure model=%s latency_ms=%.1f",
            target_model,
            latency_ms,
        )
        return PrepareLLMResult(text="".join(texts), model=self.deployment, warnings=[], tokens=tokens)
