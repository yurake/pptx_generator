from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BriefPolicyError(RuntimeError):
    """ブリーフポリシー定義の読み込みエラー。"""


@dataclass(slots=True)
class BriefPolicyChapter:
    """ポリシーが定める章の定義。"""

    id: str
    title: str
    story_phase: str | None = None


@dataclass(slots=True)
class BriefPolicy:
    """BriefCard 生成時に参照するポリシー。"""

    id: str
    name: str
    story_framework: list[str]
    prompt_template_id: str | None = None
    chapters: list[BriefPolicyChapter] = None

    def resolve_story_phase(self, index: int) -> str:
        if self.chapters and 0 <= index < len(self.chapters):
            candidate = self.chapters[index].story_phase
            if candidate:
                return candidate
        if self.story_framework:
            position = index % len(self.story_framework)
            return self.story_framework[position]
        return "introduction"

    def resolve_chapter_title(self, index: int, fallback: str) -> str:
        if self.chapters and 0 <= index < len(self.chapters):
            return self.chapters[index].title
        return fallback


@dataclass(slots=True)
class BriefPolicySet:
    default_policy_id: str
    policies: dict[str, BriefPolicy]

    def get_policy(self, policy_id: str | None) -> BriefPolicy:
        target = policy_id or self.default_policy_id
        if target not in self.policies:
            raise BriefPolicyError(f"ポリシー ID '{target}' が見つかりません。")
        return self.policies[target]


def load_brief_policy_set(path: Path | str) -> BriefPolicySet:
    policy_path = Path(path)
    if not policy_path.exists():
        raise BriefPolicyError(f"ポリシーファイルが見つかりません: {policy_path}")
    raw_text = policy_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise BriefPolicyError(f"ポリシーファイルの解析に失敗しました: {policy_path}") from exc
    default_id = payload.get("default_policy_id")
    if not default_id:
        raise BriefPolicyError("default_policy_id が定義されていません。")
    policies: dict[str, BriefPolicy] = {}
    for item in payload.get("policies", []):
        try:
            policy = _build_policy(item)
        except KeyError as exc:
            raise BriefPolicyError(f"ポリシー定義に必須項目がありません: {item}") from exc
        policies[policy.id] = policy
    if default_id not in policies:
        raise BriefPolicyError(f"default_policy_id '{default_id}' は policies に含まれていません。")
    return BriefPolicySet(default_policy_id=default_id, policies=policies)


def _build_policy(payload: dict[str, Any]) -> BriefPolicy:
    chapters_payload = payload.get("chapters") or []
    chapters = [
        BriefPolicyChapter(
            id=str(item.get("id")),
            title=str(item.get("title")),
            story_phase=item.get("story_phase"),
        )
        for item in chapters_payload
        if item.get("id") and item.get("title")
    ]
    framework = payload.get("story_framework") or [
        "introduction",
        "problem",
        "solution",
        "impact",
    ]
    return BriefPolicy(
        id=str(payload["id"]),
        name=str(payload.get("name") or payload["id"]),
        story_framework=[str(s).lower() for s in framework],
        prompt_template_id=payload.get("prompt_template_id"),
        chapters=chapters,
    )
