"""レイアウトAI向けプロンプト生成ヘルパー。"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .client import LayoutAIRequest


logger = logging.getLogger(__name__)

LAYOUT_SYSTEM_PROMPT = (
    "あなたは B2B プレゼン資料のレイアウト推薦エージェントです。"
    "入力される JSON 情報を解析し、最も適したレイアウトを高精度に提案してください。"
    "応答は JSON オブジェクトのみで返し、次のスキーマを厳守してください: "
    '{"recommended":[{"layout_id":"<候補ID>","score":0.0,"tags":["title"]}],"reasons":{"<候補ID>":"根拠"}}.'
    "tags には入力で指定された allowed_tags の語彙を使用し、score は 0〜1 の範囲で数値にしてください。"
    "recommended 以外のキーやコードフェンス、説明文は含めてはいけません。"
)


def build_system_prompt(_request: "LayoutAIRequest") -> str:
    """レイアウトAIへ渡すシステムプロンプトを生成する。"""

    return LAYOUT_SYSTEM_PROMPT


def build_user_prompt(request: "LayoutAIRequest") -> str:
    """カード情報とポリシーからレイアウトAI用のユーザープロンプトを構築する。"""

    usage_tags_reference = _build_usage_tags_reference(request.card_payload)
    payload: Dict[str, Any] = {
        "card": request.card_payload,
        "candidate_layouts": request.layout_candidates,
        "instruction": request.prompt,
    }
    if usage_tags_reference:
        payload["usage_tags_reference"] = usage_tags_reference
    if request.layout_metadata:
        payload["layout_metadata"] = request.layout_metadata

    usage_tags_text = _format_usage_tags_text(usage_tags_reference)
    if usage_tags_text and request.policy.usage_tags_template:
        payload["usage_tags_prompt"] = _apply_policy_template(
            request.policy.usage_tags_template,
            usage_tags=usage_tags_text,
        )

    card_context = _build_card_context_info(request.card_payload)
    if card_context:
        payload["card_context"] = card_context
        card_context_text = json.dumps(
            card_context, ensure_ascii=False, indent=2)
        if request.policy.card_context_template:
            payload["card_context_prompt"] = _apply_policy_template(
                request.policy.card_context_template,
                card_context=card_context_text,
            )

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _apply_policy_template(template: str, **kwargs: object) -> str:
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError) as exc:  # pragma: no cover - defensive log only
        logger.debug("layout AI policy template format failed: %s", exc)
        return template


def _build_usage_tags_reference(card_payload: Dict[str, Any]) -> List[Dict[str, str]]:
    allowed = card_payload.get("allowed_tags") or []
    details = card_payload.get("allowed_tags_detail") or {}
    if not isinstance(allowed, list):
        return []

    reference: List[Dict[str, str]] = []
    if not isinstance(details, dict):
        details = {}

    for tag in allowed:
        if not isinstance(tag, str):
            continue
        entry: Dict[str, str] = {"tag": tag}
        description = details.get(tag)
        if isinstance(description, str) and description.strip():
            entry["description"] = description.strip()
        reference.append(entry)
    return reference


def _format_usage_tags_text(reference: List[Dict[str, str]]) -> str:
    if not reference:
        return ""
    lines: List[str] = []
    for entry in reference:
        tag = entry.get("tag")
        if not tag:
            continue
        description = entry.get("description", "")
        if description:
            lines.append(f"- {tag}: {description}")
        else:
            lines.append(f"- {tag}")
    return "\n".join(lines)


def _build_card_context_info(_card_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {}
