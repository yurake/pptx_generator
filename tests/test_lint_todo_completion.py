from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.lint_todo_completion import (
    lint_todo_content,
    lint_todo_directory,
    list_todo_files,
)


def test_lint_todo_content_all_complete() -> None:
    content = """
---
meta: test
---

- [x] 作業 A
- [x] 作業 B
- [x] PR 作成
"""
    issues = lint_todo_content(content)
    assert issues == ["全チェックが完了しているにも関わらずアーカイブされていません"]


def test_lint_todo_content_only_pr_remaining() -> None:
    content = """
- [x] 作業 A
- [ ] PR 作成
"""
    issues = lint_todo_content(content)
    assert issues == ["PR 作成以外が完了しており、PR 作成のみ未完です"]


def test_lint_todo_content_with_open_tasks() -> None:
    content = """
- [x] 作業 A
- [ ] 作業 B
- [ ] PR 作成
"""
    issues = lint_todo_content(content)
    assert issues == []


def test_lint_todo_directory_ignores_non_todo_files(tmp_path: Path) -> None:
    todo_dir = tmp_path / "docs" / "todo"
    todo_dir.mkdir(parents=True)

    readme = todo_dir / "README.md"
    readme.write_text("# guide", encoding="utf-8")

    todo_file = todo_dir / "20250101-sample.md"
    todo_file.write_text("- [x] すべて実施\n- [x] PR 作成\n", encoding="utf-8")

    files = list_todo_files(todo_dir)
    assert files == [todo_file]

    results = lint_todo_directory(todo_dir)
    assert todo_file in results
    assert results[todo_file] == ["全チェックが完了しているにも関わらずアーカイブされていません"]


def test_lint_todo_directory_only_pr_remaining(tmp_path: Path) -> None:
    todo_dir = tmp_path / "docs" / "todo"
    todo_dir.mkdir(parents=True)

    todo_file = todo_dir / "20250102-sample.md"
    todo_file.write_text("- [x] 作業 A\n- [ ] PR 作成\n", encoding="utf-8")

    results = lint_todo_directory(todo_dir)
    assert todo_file in results
    assert results[todo_file] == ["PR 作成以外が完了しており、PR 作成のみ未完です"]


def test_lint_todo_directory_ok(tmp_path: Path) -> None:
    todo_dir = tmp_path / "docs" / "todo"
    todo_dir.mkdir(parents=True)

    todo_file = todo_dir / "20250103-sample.md"
    todo_file.write_text("- [x] 作業 A\n- [ ] 作業 B\n", encoding="utf-8")

    results = lint_todo_directory(todo_dir)
    assert results == {}
