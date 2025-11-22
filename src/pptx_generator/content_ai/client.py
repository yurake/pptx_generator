"""生成 AI クライアントの抽象化と実装集。"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Protocol

from ..models import JobSpec, Slide
from .policy import ContentAIPolicy

logger = logging.getLogger(__name__)

_LLM_LOGGER = logging.getLogger("pptx_generator.content_ai.llm")

MAX_BODY_LINES = 6
MAX_BODY_LENGTH = 40
MAX_TITLE_LENGTH = 120
DEFAULT_MAX_TOKENS = 32000


class LLMClientConfigurationError(RuntimeError):
    """LLM クライアントの初期化に失敗した場合の例外。"""


@dataclass(slots=True)
class AIGenerationRequest:
    """LLM へのリクエスト。"""

    prompt: str
    policy: ContentAIPolicy
    spec: JobSpec
    slide: Slide
    intent: str
    reference_text: str | None = None


@dataclass(slots=True)
class AIGenerationResponse:
    """LLM からの応答。"""

    title: str
    body: list[str] = field(default_factory=list)
    note: str | None = None
    intent: str | None = None
    model: str = "mock-local"
    warnings: list[str] = field(default_factory=list)
    raw_text: str | None = None


@dataclass(slots=True)
class SlideMatchCandidate:
    """スライド ID 整合の候補情報。"""

    slide_id: str
    title: str | None = None
    layout: str | None = None
    subtitle: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class SlideMatchRequest:
    """スライド ID 整合用のリクエスト。"""

    card_id: str
    card_chapter: str | None
    card_intent: tuple[str, ...]
    card_story_phase: str | None
    card_summary: str
    prompt: str
    system_prompt: str
    candidates: list[SlideMatchCandidate]
    model: str | None = None


@dataclass(slots=True)
class SlideMatchResponse:
    """スライド ID 整合の応答。"""

    slide_id: str | None
    confidence: float
    reason: str | None
    model: str = "mock-local"
    warnings: list[str] = field(default_factory=list)
    raw_text: str | None = None


class LLMClient(Protocol):
    """生成 AI クライアント共通インターフェース。"""

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        """リクエストに基づきスライド候補を生成する。"""

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        """カードと JobSpec スライドの対応付けを推論する。"""


def create_llm_client() -> LLMClient:
    """環境変数に基づき LLM クライアントを生成する。"""

    provider = os.getenv("PPTX_LLM_PROVIDER", "mock").strip().lower()
    _LLM_LOGGER.info("LLM provider resolved: %s", provider)
    if provider in {"", "mock", "mock-local"}:
        return MockLLMClient()
    if provider in {"openai", "openai-api"}:
        return OpenAIChatClient.from_env()
    if provider in {"azure-openai", "azure"}:
        return AzureOpenAIChatClient.from_env()
    if provider in {"claude", "anthropic"}:
        return AnthropicClaudeClient.from_env()
    if provider in {"aws-claude", "bedrock"}:
        return AwsClaudeClient.from_env()
    msg = f"未知の LLM プロバイダーが指定されました: {provider}"
    raise LLMClientConfigurationError(msg)


def _truncate(value: str, max_length: int) -> str:
    normalized = value.strip()
    if len(normalized) <= max_length:
        return normalized
    ellipsis = "..."
    if max_length <= len(ellipsis):
        return ellipsis[:max_length]
    return normalized[: max_length - len(ellipsis)] + ellipsis


def _normalize_body(candidates: list[str]) -> tuple[list[str], list[str]]:
    """本文候補を正規化し、長さ制限を満たすように整形する。"""

    body_lines: list[str] = []
    warnings: list[str] = []

    for candidate in candidates:
        text = str(candidate).strip()
        if not text:
            continue
        if len(body_lines) >= MAX_BODY_LINES:
            warnings.append("body_lines_truncated")
            break
        if len(text) > MAX_BODY_LENGTH:
            warnings.append("body_line_length_truncated")
            text = text[:MAX_BODY_LENGTH]
        body_lines.append(text)

    if not body_lines:
        body_lines.append("自動生成コンテンツ")

    return body_lines, warnings


def _build_user_prompt(request: AIGenerationRequest) -> str:
    instructions = request.policy.safeguards.get("user_instructions") if isinstance(request.policy.safeguards, dict) else None
    guidance = instructions or textwrap.dedent(
        """
        以下の要件を必ず守って JSON 形式で回答してください。
        - JSON オブジェクトのキーは title, body, note。
        - body は文字列の配列で最大6行、各行40文字以内。
        - note が不要な場合は null を指定。
        - 日本語で回答する。
        """
    ).strip()
    reference_section = ""
    if request.reference_text:
        reference_section = f"\n\n# 参考テキスト\n{request.reference_text}"
    return f"{guidance}\n\n# スライド情報\n{request.prompt}{reference_section}"


def _build_system_prompt(request: AIGenerationRequest) -> str:
    safeguards = request.policy.safeguards if isinstance(request.policy.safeguards, dict) else {}
    default_prompt = "あなたは B2B プレゼン資料のコンテンツ作成を支援する専門アシスタントです。"
    return str(safeguards.get("system_prompt", default_prompt))


def _extract_json_from_text(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _build_response_from_text(
    text: str,
    request: AIGenerationRequest,
    *,
    model: str,
    finish_reason: str | None = None,
    refusal: str | None = None,
) -> AIGenerationResponse:
    _LLM_LOGGER.info(
        "LLM response received",
        extra={
            "slide_id": request.slide.id,
            "model": model,
            "policy_id": request.policy.id,
            "intent": request.intent,
            "raw_response": text,
            "finish_reason": finish_reason or "",
            "refusal": refusal or "",
        },
    )
    warnings: list[str] = []
    if not text and refusal:
        warnings.append("response_refused")
        text = refusal
    elif not text and finish_reason and finish_reason != "stop":
        warnings.append(f"finish_{finish_reason}")
    data: dict[str, object]
    try:
        data = _extract_json_from_text(text)
    except json.JSONDecodeError:
        warnings.append("response_not_json")
        lines = [line.strip("-• ") for line in text.splitlines() if line.strip()]
        title_source = lines[0] if lines else request.slide.title or request.prompt
        body_candidates = lines[1:] if len(lines) > 1 else lines
        body, body_warnings = _normalize_body(body_candidates)
        warnings.extend(body_warnings)
        return AIGenerationResponse(
            title=_truncate(title_source, MAX_TITLE_LENGTH),
            body=body,
            note=None,
            intent=request.intent,
            model=model,
            warnings=warnings,
            raw_text=text,
        )

    title_source = data.get("title") or request.slide.title or request.spec.meta.title
    body_candidates = data.get("body")
    if isinstance(body_candidates, list):
        body_raw = [str(item) for item in body_candidates]
    elif body_candidates is None:
        body_raw = []
    else:
        body_raw = [str(body_candidates)]
        warnings.append("body_not_array")

    body, body_warnings = _normalize_body(body_raw)
    warnings.extend(body_warnings)

    note_value = data.get("note")
    note = None if note_value in (None, "", "null") else str(note_value)

    intent_value = data.get("intent")
    intent = str(intent_value) if isinstance(intent_value, str) else request.intent

    return AIGenerationResponse(
        title=_truncate(str(title_source), MAX_TITLE_LENGTH),
        body=body,
        note=note,
        intent=intent,
        model=model,
        warnings=warnings,
        raw_text=text,
    )


def _normalize_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return confidence


def _build_slide_match_response(
    text: str,
    request: SlideMatchRequest,
    *,
    model: str,
    finish_reason: str | None = None,
    refusal: str | None = None,
) -> SlideMatchResponse:
    _LLM_LOGGER.info(
        "LLM slide match response",
        extra={
            "card_id": request.card_id,
            "model": model,
            "raw_response": text,
            "finish_reason": finish_reason or "",
            "refusal": refusal or "",
        },
    )
    warnings: list[str] = []
    if not text and refusal:
        warnings.append("response_refused")
        text = refusal
    elif not text and finish_reason and finish_reason != "stop":
        warnings.append(f"finish_{finish_reason}")

    if not text:
        return SlideMatchResponse(
            slide_id=None,
            confidence=0.0,
            reason=refusal,
            model=model,
            warnings=warnings,
            raw_text=text,
        )

    try:
        data = _extract_json_from_text(text)
    except json.JSONDecodeError:
        warnings.append("response_not_json")
        return SlideMatchResponse(
            slide_id=None,
            confidence=0.0,
            reason=text.strip() or refusal,
            model=model,
            warnings=warnings,
            raw_text=text,
        )

    slide_id_value = (
        data.get("slide_id")
        or data.get("recommended_slide_id")
        or data.get("slideId")
        or data.get("match")
    )
    slide_id = str(slide_id_value).strip() if slide_id_value else None
    reason_value = data.get("reason") or data.get("explanation")
    reason = str(reason_value).strip() if isinstance(reason_value, str) else None
    confidence = _normalize_confidence(data.get("confidence") or data.get("score"))

    candidate_ids = {candidate.slide_id for candidate in request.candidates}
    if slide_id and slide_id not in candidate_ids:
        warnings.append("unknown_slide_id")

    return SlideMatchResponse(
        slide_id=slide_id if slide_id in candidate_ids else None,
        confidence=confidence if slide_id in candidate_ids else 0.0,
        reason=reason,
        model=model,
        warnings=warnings,
        raw_text=text,
    )


class MockLLMClient:
    """開発用のモック LLM クライアント。"""

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        slide = request.slide
        title_source = slide.title or f"{request.spec.meta.title} ({slide.id})"
        title = _truncate(title_source, MAX_TITLE_LENGTH)

        bullet_texts: list[str] = []
        for group in slide.iter_bullet_groups():
            for item in group.items:
                bullet_texts.append(item.text)

        if not bullet_texts:
            bullet_texts.append(request.prompt)

        if request.reference_text:
            reference_lines = [line.strip() for line in request.reference_text.splitlines() if line.strip()]
            bullet_texts.extend(reference_lines)

        body, warnings = _normalize_body(bullet_texts)
        note = (
            f"{request.policy.name} ポリシーを使用して自動生成しました。"
            if request.policy.name
            else None
        )

        raw_payload = {
            "title": title,
            "body": body,
            "note": note,
            "intent": request.intent,
        }
        return AIGenerationResponse(
            title=title,
            body=body,
            note=note,
            intent=request.intent,
            model=request.policy.model,
            warnings=warnings,
            raw_text=json.dumps(raw_payload, ensure_ascii=False),
        )

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        if not request.candidates:
            return SlideMatchResponse(
                slide_id=None,
                confidence=0.0,
                reason="no candidates",
                model="mock-local",
            )

        def score_candidate(candidate: SlideMatchCandidate) -> float:
            score = 0.0
            if candidate.slide_id == request.card_id:
                score += 5.0
            title = (candidate.title or "").lower()
            chapter = (request.card_chapter or "").lower()
            if chapter and chapter in title:
                score += 3.0
            summary = request.card_summary.lower()
            if title and summary:
                ratio = SequenceMatcher(None, title, summary[: len(title)]).ratio()
                score += ratio * 2.0
            if request.card_story_phase:
                phase = request.card_story_phase.lower()
                layout = (candidate.layout or "").lower()
                if phase in layout or layout.startswith(phase[:3]):
                    score += 1.0
            if request.card_intent:
                for intent in request.card_intent:
                    if intent and intent.lower() in title:
                        score += 1.0
            return score

        scored = [(score_candidate(candidate), candidate) for candidate in request.candidates]
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_candidate = scored[0]
        if best_score <= 0:
            return SlideMatchResponse(
                slide_id=None,
                confidence=0.0,
                reason="heuristic match not found",
                model="mock-local",
            )
        confidence = min(1.0, best_score / 5.0)
        return SlideMatchResponse(
            slide_id=best_candidate.slide_id,
            confidence=confidence,
            reason=f"heuristic score={best_score:.2f}",
            model="mock-local",
        )


class OpenAIChatClient:
    """OpenAI Chat Completions API クライアント。"""

    def __init__(self, client, *, model: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "OpenAIChatClient":
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "openai パッケージが必要です。`pip install openai` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMClientConfigurationError("OPENAI_API_KEY が設定されていません")

        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        return cls(client, model=model, temperature=temperature, max_tokens=max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        messages = [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        model_name = request.policy.model or self._model
        if model_name == "mock-local":
            model_name = self._model
        kwargs: dict[str, object] = {
            "model": model_name,
            "messages": messages,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            kwargs["max_completion_tokens"] = self._max_tokens
        for _ in range(3):
            try:
                response = self._client.chat.completions.create(  # type: ignore[attr-defined]
                    **kwargs,
                )
                break
            except Exception as exc:  # noqa: BLE001
                _LLM_LOGGER.warning(
                    "OpenAI chat completion error: %s",
                    exc,
                    extra={
                        "model": model_name,
                        "slide_id": request.slide.id,
                    },
                )
                message = str(exc).lower()
                if (
                    "max_completion_tokens" in message
                    and "max_tokens" in message
                    and "max_completion_tokens" in kwargs
                ):
                    kwargs.pop("max_completion_tokens", None)
                    if self._max_tokens > 0:
                        kwargs["max_tokens"] = self._max_tokens
                    continue
                if (
                    "max_tokens" in message
                    and "max_completion_tokens" in message
                    and "max_tokens" in kwargs
                ):
                    kwargs.pop("max_tokens", None)
                    if self._max_tokens > 0:
                        kwargs["max_completion_tokens"] = self._max_tokens
                    continue
                if "temperature" in message and "unsupported" in message:
                    kwargs["temperature"] = 1.0
                    continue
                if "response_format" in message and "not" in message and "support" in message:
                    kwargs.pop("response_format", None)
                    continue
                raise
        else:  # pragma: no cover - safeguard
            raise RuntimeError("OpenAI API call failed after applying compatibility fallbacks")
        choice = response.choices[0]  # type: ignore[index]
        message = choice.message
        content = getattr(message, "content", None)
        if isinstance(content, str):
            text = content
        elif content is None:
            text = ""
        else:
            text = "".join(str(part) for part in content)
        return _build_response_from_text(
            text,
            request,
            model=model_name,
            finish_reason=getattr(choice, "finish_reason", None),
            refusal=getattr(message, "refusal", None),
        )

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt},
        ]
        model_name = request.model or self._model
        if model_name == "mock-local":
            model_name = self._model
        kwargs: dict[str, object] = {
            "model": model_name,
            "messages": messages,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            kwargs["max_completion_tokens"] = self._max_tokens
        for _ in range(3):
            try:
                response = self._client.chat.completions.create(  # type: ignore[attr-defined]
                    **kwargs,
                )
                break
            except Exception as exc:  # noqa: BLE001
                _LLM_LOGGER.warning(
                    "OpenAI chat completion error: %s",
                    exc,
                    extra={
                        "model": model_name,
                        "card_id": request.card_id,
                    },
                )
                message = str(exc).lower()
                if (
                    "max_completion_tokens" in message
                    and "max_tokens" in message
                    and "max_completion_tokens" in kwargs
                ):
                    kwargs.pop("max_completion_tokens", None)
                    if self._max_tokens > 0:
                        kwargs["max_tokens"] = self._max_tokens
                    continue
                if (
                    "max_tokens" in message
                    and "max_completion_tokens" in message
                    and "max_tokens" in kwargs
                ):
                    kwargs.pop("max_tokens", None)
                    if self._max_tokens > 0:
                        kwargs["max_completion_tokens"] = self._max_tokens
                    continue
                if "response_format" in message and "not" in message and "support" in message:
                    kwargs.pop("response_format", None)
                    continue
                raise
        else:  # pragma: no cover - safeguard
            raise RuntimeError("OpenAI API match call failed after applying compatibility fallbacks")
        choice = response.choices[0]  # type: ignore[index]
        message = choice.message
        content = getattr(message, "content", None)
        if isinstance(content, str):
            text = content
        elif content is None:
            text = ""
        else:
            text = "".join(str(part) for part in content)
        return _build_slide_match_response(
            text,
            request,
            model=model_name,
            finish_reason=getattr(choice, "finish_reason", None),
            refusal=getattr(message, "refusal", None),
        )


class AzureOpenAIChatClient:
    """Azure OpenAI Chat Completions API クライアント。"""

    def __init__(
        self,
        client,
        *,
        deployment: str,
        api_version: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._api_version = api_version
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "AzureOpenAIChatClient":
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "openai パッケージが必要です。`pip install openai` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not all([endpoint, api_key, deployment]):
            raise LLMClientConfigurationError(
                "AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY/AZURE_OPENAI_DEPLOYMENT を設定してください"
            )
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        endpoint = endpoint.rstrip("/")
        lowered = endpoint.lower()
        for suffix in ("/openai/responses", "/openai"):
            if lowered.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                lowered = endpoint.lower()
        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        return cls(client, deployment=deployment, api_version=api_version, temperature=temperature, max_tokens=max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        messages = [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        deployment = request.policy.model or self._deployment
        if deployment == "mock-local":
            deployment = self._deployment
        from openai.types.responses import ResponseOutputMessage
        from openai.types.responses.response_output_text import ResponseOutputText
        from openai.types.responses.response_output_refusal import ResponseOutputRefusal

        kwargs: dict[str, object] = {
            "model": deployment,
            "input": messages,
            "temperature": self._temperature,
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens
        response = self._client.responses.create(  # type: ignore[attr-defined]
            **kwargs,
        )

        text_segments: list[str] = []
        refusal_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):
                        refusal_segments.append(content.refusal)

        raw_text = "\n".join(segment.strip() for segment in text_segments if segment.strip())
        refusal_text = "\n".join(segment.strip() for segment in refusal_segments if segment.strip()) or None
        return _build_response_from_text(
            raw_text,
            request,
            model=deployment,
            finish_reason=(response.incomplete_details.reason if getattr(response, "incomplete_details", None) else None),
            refusal=refusal_text,
        )

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        from openai.types.responses import ResponseOutputMessage
        from openai.types.responses.response_output_text import ResponseOutputText
        from openai.types.responses.response_output_refusal import ResponseOutputRefusal

        deployment = request.model or self._deployment
        if deployment == "mock-local":
            deployment = self._deployment
        kwargs: dict[str, object] = {
            "model": deployment,
            "input": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": self._temperature,
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens
        response = self._client.responses.create(  # type: ignore[attr-defined]
            **kwargs,
        )

        text_segments: list[str] = []
        refusal_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):
                        refusal_segments.append(content.refusal)

        raw_text = "\n".join(segment.strip() for segment in text_segments if segment.strip())
        refusal_text = "\n".join(segment.strip() for segment in refusal_segments if segment.strip()) or None
        return _build_slide_match_response(
            raw_text,
            request,
            model=deployment,
            finish_reason=(response.incomplete_details.reason if getattr(response, "incomplete_details", None) else None),
            refusal=refusal_text,
        )


class AnthropicClaudeClient:
    """Anthropic Claude API クライアント。"""

    def __init__(self, client, *, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "AnthropicClaudeClient":
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "anthropic パッケージが必要です。`pip install anthropic` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMClientConfigurationError("ANTHROPIC_API_KEY が設定されていません")
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        client = Anthropic(api_key=api_key)
        return cls(client, model=model, max_tokens=max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_user_prompt(request),
                    }
                ],
            }
        ]
        model_name = request.policy.model or self._model
        if model_name == "mock-local":
            model_name = self._model
        response = self._client.messages.create(  # type: ignore[attr-defined]
            model=model_name,
            system=_build_system_prompt(request),
            max_tokens=self._max_tokens,
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.3")),
            messages=messages,
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "\n".join(text_parts)
        return _build_response_from_text(text, request, model=model_name)

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        model_name = request.model or self._model
        if model_name == "mock-local":
            model_name = self._model
        response = self._client.messages.create(  # type: ignore[attr-defined]
            model=model_name,
            system=request.system_prompt,
            max_tokens=self._max_tokens,
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.3")),
            messages=[
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
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "\n".join(text_parts)
        return _build_slide_match_response(text, request, model=model_name)


class AwsClaudeClient:
    """AWS Bedrock Claude クライアント。"""

    def __init__(
        self,
        runtime_client,
        *,
        model_id: str,
        max_tokens: int,
        inference_profile_arn: str | None,
    ) -> None:
        self._client = runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._inference_profile_arn = inference_profile_arn

    @classmethod
    def from_env(cls) -> "AwsClaudeClient":
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "boto3 パッケージが必要です。`pip install boto3` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        model_id = os.getenv("AWS_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        inference_profile_arn = os.getenv("AWS_CLAUDE_INFERENCE_PROFILE_ARN")
        region = os.getenv("AWS_REGION")
        profile = os.getenv("AWS_PROFILE")

        session_kwargs: dict[str, object] = {}
        if profile:
            session_kwargs["profile_name"] = profile
        if region:
            session_kwargs["region_name"] = region
        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise LLMClientConfigurationError(
                "AWS 認証情報が見つかりません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定するか、`aws configure` で設定してください。"
            )

        client_kwargs: dict[str, object] = {}
        if region:
            client_kwargs["region_name"] = region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise LLMClientConfigurationError(
                "AWS 認証情報を利用できません。環境変数または共有クレデンシャルで設定してください。"
            ) from exc
        max_tokens = int(os.getenv("AWS_CLAUDE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        return cls(
            runtime_client,
            model_id=model_id,
            max_tokens=max_tokens,
            inference_profile_arn=inference_profile_arn,
        )

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": float(os.getenv("AWS_CLAUDE_TEMPERATURE", "0.3")),
            "system": _build_system_prompt(request),
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
        model_id = request.policy.model or self._model_id
        if model_id == "mock-local":
            model_id = self._model_id
        invoke_kwargs = {
            "modelId": model_id,
            "body": json.dumps(payload),
            "contentType": "application/json",
            "accept": "application/json",
        }
        if self._inference_profile_arn:
            invoke_kwargs["inferenceProfileArn"] = self._inference_profile_arn

        try:
            response = self._client.invoke_model(**invoke_kwargs)
        except Exception as exc:  # pragma: no cover - AWS runtime errors
            from botocore.exceptions import NoCredentialsError

            if isinstance(exc, NoCredentialsError):
                raise LLMClientConfigurationError(
                    "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
                ) from exc
            raise
        body = response.get("body")
        if hasattr(body, "read"):
            body_text = body.read()
        else:  # pragma: no cover - unexpected response type
            body_text = body
        data = json.loads(body_text)
        contents = data.get("content", [])
        text_parts = [item.get("text", "") for item in contents if isinstance(item, dict)]
        text = "\n".join(text_parts)
        return _build_response_from_text(text, request, model=model_id)

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": float(os.getenv("AWS_CLAUDE_TEMPERATURE", "0.3")),
            "system": request.system_prompt,
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
        model_id = request.model or self._model_id
        if model_id == "mock-local":
            model_id = self._model_id
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
        if hasattr(body, "read"):
            body_text = body.read()
        else:  # pragma: no cover - unexpected response type
            body_text = body
        data = json.loads(body_text)
        contents = data.get("content", [])
        text_parts = [item.get("text", "") for item in contents if isinstance(item, dict)]
        text = "\n".join(text_parts)
        return _build_slide_match_response(text, request, model=model_id)


__all__ = [
    "AIGenerationRequest",
    "AIGenerationResponse",
    "SlideMatchCandidate",
    "SlideMatchRequest",
    "SlideMatchResponse",
    "LLMClient",
    "LLMClientConfigurationError",
    "MockLLMClient",
    "create_llm_client",
]
