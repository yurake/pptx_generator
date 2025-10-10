"""ToDo ファイルの残存チェック用スクリプト."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List

TODO_FILENAME_RE = re.compile(r"^[0-9]{8}-[A-Za-z0-9_-]+\.md$")
CHECKBOX_RE = re.compile(r"^(- \[(?: |x)\] .*)$", re.MULTILINE)


def list_todo_files(todo_dir: Path) -> List[Path]:
    return sorted(
        path
        for path in todo_dir.iterdir()
        if path.is_file() and TODO_FILENAME_RE.match(path.name)
    )


def lint_todo_content(content: str) -> List[str]:
    lines = [match.group(1) for match in CHECKBOX_RE.finditer(content)]
    if not lines:
        return []

    unchecked = [line for line in lines if line.startswith("- [ ]")]
    issues: List[str] = []

    if unchecked:
        if len(unchecked) == 1 and "PR 作成" in unchecked[0]:
            issues.append("PR 作成以外が完了しており、PR 作成のみ未完です")
    else:
        issues.append("全チェックが完了しているにも関わらずアーカイブされていません")

    return issues


def lint_todo_file(path: Path) -> List[str]:
    content = path.read_text(encoding="utf-8")
    return lint_todo_content(content)


def lint_todo_directory(todo_dir: Path) -> Dict[Path, List[str]]:
    results: Dict[Path, List[str]] = {}
    for path in list_todo_files(todo_dir):
        issues = lint_todo_file(path)
        if issues:
            results[path] = issues
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="ToDo 残存チェック")
    parser.add_argument(
        "--todo-dir", default="docs/todo", help="チェック対象の ToDo ディレクトリ"
    )
    args = parser.parse_args()

    todo_dir = Path(args.todo_dir)
    if not todo_dir.exists():
        print(f"ToDo ディレクトリが見つかりません: {todo_dir}", file=sys.stderr)
        sys.exit(1)

    results = lint_todo_directory(todo_dir)
    if results:
        print("ToDo 残存チェックで問題を検出しました:\n")
        for path, issues in results.items():
            for issue in issues:
                print(f"- {path}: {issue}")
        sys.exit(1)

    print("ToDo 残存チェックに問題はありません。")


if __name__ == "__main__":
    main()
