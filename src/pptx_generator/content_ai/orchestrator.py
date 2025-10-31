"""コンテンツ生成 AI のオーケストレーション。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from ..models import (ContentApprovalDocument, ContentDocumentMeta,
                      ContentElements, ContentSlide, JobSpec)
from .client import (AIGenerationRequest, AIGenerationResponse, LLMClient,
                     create_llm_client)
from .policy import ContentAIPolicy, ContentAIPolicyError, ContentAIPolicySet


logger = logging.getLogger(__name__)


class ContentAIOrchestrationError(RuntimeError):
    """オーケストレーション全体の例外。"""


class ContentAIOrchestrator:
    """ポリシーと LLM クライアントを用いてスライド候補を生成する。"""

    def __init__(
        self,
        policy_set: ContentAIPolicySet,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._policy_set = policy_set
        self._llm_client = llm_client or create_llm_client()

    def generate_document(
        self,
        spec: JobSpec,
        *,
        policy_id: str | None = None,
        reference_text: str | None = None,
    ) -> tuple[ContentApprovalDocument, dict[str, Any], list[dict[str, Any]]]:
        """指定ポリシーでコンテンツ案を生成する。"""

        try:
            policy = self._policy_set.get_policy(policy_id)
        except ContentAIPolicyError as exc:
            raise ContentAIOrchestrationError(str(exc)) from exc

        slides: list[ContentSlide] = []
        logs: list[dict[str, Any]] = []

        for spec_slide in spec.slides:
            prompt = _render_prompt(
                template=policy.resolve_prompt(spec_slide.layout),
                spec=spec,
                slide=spec_slide,
            )
            intent = policy.resolve_intent(spec_slide.layout)
            request = AIGenerationRequest(
                prompt=prompt,
                policy=policy,
                spec=spec,
                slide=spec_slide,
                intent=intent,
                reference_text=reference_text,
            )

            if logger.isEnabledFor(logging.INFO):
                logger.info(
                    "AI Request: slide_id=%s policy_id=%s intent=%s prompt=%s",
                    spec_slide.id,
                    policy.id,
                    intent,
                    prompt,
                )

            response = self._llm_client.generate(request)
            content_slide = _build_content_slide(spec_slide.id, response, intent)
            slides.append(content_slide)
            if logger.isEnabledFor(logging.INFO):
                logger.info(
                    "AI Response: slide_id=%s model=%s intent=%s title=%s body=%s warnings=%s",
                    spec_slide.id,
                    response.model,
                    content_slide.intent,
                    response.title,
                    response.body,
                    response.warnings,
                )
            logs.append(
                {
                    "slide_id": spec_slide.id,
                    "layout": spec_slide.layout,
                    "prompt": prompt,
                    "policy_id": policy.id,
                    "model": response.model,
                    "intent": content_slide.intent,
                    "warnings": response.warnings,
                }
            )

        document = ContentApprovalDocument(
            slides=slides,
            meta=_build_document_meta(spec, policy),
        )
        meta_payload = _build_generation_meta(spec, policy, document, logs)
        return document, meta_payload, logs


def _render_prompt(*, template: str, spec: JobSpec, slide) -> str:
    """テンプレートへ Spec 情報を埋め込み、プロンプトを生成する。"""

    mapping = {
        "spec_title": spec.meta.title,
        "spec_client": spec.meta.client or "",
        "slide_id": slide.id,
        "slide_title": slide.title or "",
        "slide_layout": slide.layout,
    }
    try:
        return template.format(**mapping)
    except (KeyError, IndexError):
        return template


def _build_content_slide(
    slide_id: str,
    response: AIGenerationResponse,
    fallback_intent: str,
) -> ContentSlide:
    intent = response.intent or fallback_intent
    elements = ContentElements(
        title=response.title,
        body=response.body,
        table_data=None,
        note=response.note,
    )
    return ContentSlide(
        id=slide_id,
        intent=intent,
        type_hint=None,
        elements=elements,
        status="draft",
        ai_review=None,
        applied_autofix=[],
    )


def _build_document_meta(spec: JobSpec, policy: ContentAIPolicy) -> ContentDocumentMeta:
    safeguard_tone = None
    if isinstance(policy.safeguards, dict):
        tone = policy.safeguards.get("tone")
        if isinstance(tone, str):
            safeguard_tone = tone

    summary = f"{policy.name} に基づく {spec.meta.title} の自動生成コンテンツ"
    if len(summary) > 120:
        summary = summary[:117] + "..."

    return ContentDocumentMeta(
        tone=safeguard_tone,
        audience=spec.meta.client,
        summary=summary,
    )


def _build_generation_meta(
    spec: JobSpec,
    policy: ContentAIPolicy,
    document: ContentApprovalDocument,
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    spec_dump = json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    spec_hash = sha256(spec_dump.encode("utf-8")).hexdigest()

    slides_meta: list[dict[str, Any]] = []
    for slide, log_entry in zip(document.slides, logs, strict=False):
        elements_dump = json.dumps(
            slide.elements.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
        )
        content_hash = sha256(elements_dump.encode("utf-8")).hexdigest()
        slides_meta.append(
            {
                "slide_id": slide.id,
                "intent": slide.intent,
                "content_hash": content_hash,
                "body_lines": len(slide.elements.body),
                "model": log_entry["model"],
            }
        )

    return {
        "generated_at": generated_at,
        "policy_id": policy.id,
        "policy_name": policy.name,
        "model": policy.model,
        "spec": {
            "title": spec.meta.title,
            "client": spec.meta.client,
            "hash": spec_hash,
        },
        "slides": slides_meta,
        "safeguards": policy.safeguards,
    }
