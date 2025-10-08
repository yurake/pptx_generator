from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import textwrap
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative: str):
    module_path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("モジュールの読み込みに失敗しました")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_request_stub():
    if "requests" in sys.modules:
        return
    stub = types.ModuleType("requests")

    def _request(*_args, **_kwargs):
        raise AssertionError("HTTP 呼び出しはスタブ化されています")

    stub.request = _request
    sys.modules["requests"] = stub


@pytest.fixture(scope="module")
def todo_to_issues():
    _install_request_stub()
    return _load_module("sync_todo_to_issues", "scripts/sync_todo_to_issues.py")


def test_parse_tasks(tmp_path, todo_to_issues):
    md_body = textwrap.dedent(
        """
        - [x] 完了したタスク (#12)
        - [ ] 新しいタスク
        - [X] 大文字チェック (#34)
        """
    ).strip()
    md_path = tmp_path / "todo.md"
    md_path.write_text(md_body, encoding="utf-8")

    tasks = todo_to_issues.parse_tasks(str(md_path))

    assert tasks == [
        {"title": "完了したタスク", "checked": True, "issue_number": 12},
        {"title": "新しいタスク", "checked": False, "issue_number": None},
        {"title": "大文字チェック", "checked": True, "issue_number": 34},
    ]


def test_upsert_related_issue_number_line_updates_placeholder(todo_to_issues):
    original = textwrap.dedent(
        """
        ---
        目的: テスト
        関連Issue: 未作成
        ---

        - [ ] 何かする
        """
    ).lstrip()

    updated, changed = todo_to_issues.upsert_related_issue_number_line(original, 123)

    assert changed is True
    assert "関連Issue: #123" in updated.splitlines()[2]


def test_upsert_related_issue_number_line_inserts_when_missing(todo_to_issues):
    original = textwrap.dedent(
        """
        ---
        目的: テスト
        ---

        - [ ] 何かする
        """
    ).lstrip()

    updated, changed = todo_to_issues.upsert_related_issue_number_line(original, 55)

    assert changed is True
    lines = updated.splitlines()
    assert lines[3] == "関連Issue: #55"


def test_collect_todo_paths_excludes_template(tmp_path, todo_to_issues):
    todo_dir = tmp_path / "docs" / "todo"
    (todo_dir / "archive").mkdir(parents=True)
    (todo_dir / "template.md").write_text("template", encoding="utf-8")
    (todo_dir / "README.md").write_text("readme", encoding="utf-8")
    (todo_dir / "20251008-check.md").write_text("content", encoding="utf-8")
    (todo_dir / "archive" / "old.md").write_text("old", encoding="utf-8")

    paths = todo_to_issues.collect_todo_paths([], str(todo_dir), "template.md", include_template=False)

    assert all(not p.endswith("template.md") for p in paths)
    assert all("README.md" not in p for p in paths)
    assert any(p.endswith("20251008-check.md") for p in paths)
    assert any("archive" in p and p.endswith("old.md") for p in paths)


def test_extract_tasks_and_notes(todo_to_issues):
    content = textwrap.dedent(
        """
        ---
        目的: テスト
        ---

        - [ ] タスクA
          - メモ: A

        - [x] タスクB

        ## メモ
        - note
        """
    )
    tasks, notes = todo_to_issues.extract_tasks_and_notes(content)
    assert "タスクA" in tasks
    assert "タスクB" in tasks
    assert notes.startswith("## メモ")


def test_is_legacy_issue(todo_to_issues):
    rel = "docs/todo/sample.md"
    legacy_issue = {
        "number": 12,
        "body": "This issue is managed by **docs/todo/sample.md** sync.\n\n<!-- todo-path: docs/todo/sample.md -->",
    }
    assert todo_to_issues.is_legacy_issue(legacy_issue, rel, keep_number=20)

    new_issue = {
        "number": 20,
        "body": "## title\n\n### タスク\n- [ ] test\n\n<!-- todo-path: docs/todo/sample.md -->",
    }
    assert not todo_to_issues.is_legacy_issue(new_issue, rel, keep_number=20)
