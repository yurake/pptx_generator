from __future__ import annotations

import sys
import types

if "requests" not in sys.modules:
    stub = types.SimpleNamespace()

    def _stub_request(*_args, **_kwargs):
        raise RuntimeError("requests.request stubbed in tests/test_sync_todo_to_issues.py")

    stub.request = _stub_request
    sys.modules["requests"] = stub

from scripts.sync_todo_to_issues import build_issue_title


def test_build_issue_title_with_roadmap_and_purpose():
    fields = {
        "目的": "RM-069 開発プロセス運用ルール見直し（整理）",
        "roadmap_item": "RM-069 開発プロセス運用ルール見直し",
    }
    title = build_issue_title(fields, "docs/todo/20251122-rm069-dev-process-guidance.md")
    assert title == "RM-069 開発プロセス運用ルール見直し（整理）"


def test_build_issue_title_without_rm_in_purpose():
    fields = {
        "目的": "開発プロセス運用ルール見直し（整理）",
        "roadmap_item": "RM-069 開発プロセス運用ルール見直し",
    }
    title = build_issue_title(fields, "docs/todo/20251122-rm069-dev-process-guidance.md")
    assert title.startswith("RM-069")
    assert "開発プロセス運用ルール見直し（整理）" in title


def test_build_issue_title_fallback_to_path():
    fields = {}
    rel = "docs/todo/20251122-rm069-dev-process-guidance.md"
    assert build_issue_title(fields, rel) == rel
