"""AI ポリシー読み込みのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptx_generator.content_ai import ContentAIPolicyError, load_policy_set
from pptx_generator.content_ai import prompts


def test_load_policy_set_and_resolve(tmp_path: Path) -> None:
    payload = {
        "default_policy_id": "default",
        "policies": [
            {
                "id": "default",
                "name": "テストポリシー",
                "prompt_id": "content.baseline",
                "slide_policies": [
                    {
                        "layout": "Title",
                        "intent": "cover",
                        "prompt_id": "content.cover",
                    }
                ],
            }
        ],
    }
    policy_file = tmp_path / "ai_policy.json"
    policy_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    policy_set = load_policy_set(policy_file)
    policy = policy_set.get_policy()

    assert policy.id == "default"
    assert policy.resolve_intent("Title") == "cover"
    assert policy.resolve_intent("Unknown") == policy.default_intent
    assert policy.resolve_prompt("Title") == prompts.get_prompt_template("content.cover")
    assert policy.resolve_prompt("Other") == prompts.get_prompt_template("content.baseline")


def test_get_policy_with_unknown_id() -> None:
    policy_set = load_policy_set(Path("config/content_ai_policies.json"))
    with pytest.raises(ContentAIPolicyError):
        policy_set.get_policy("unknown-policy")


def test_resolve_prompt_with_unknown_prompt_id(tmp_path: Path) -> None:
    payload = {
        "default_policy_id": "default",
        "policies": [
            {
                "id": "default",
                "name": "テストポリシー",
                "prompt_id": "content.baseline",
                "slide_policies": [
                    {
                        "layout": "Title",
                        "intent": "cover",
                        "prompt_id": "unknown.prompt",
                    }
                ],
            }
        ],
    }
    policy_file = tmp_path / "ai_policy_invalid.json"
    policy_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    policy_set = load_policy_set(policy_file)
    policy = policy_set.get_policy()

    with pytest.raises(ContentAIPolicyError):
        policy.resolve_prompt("Title")
