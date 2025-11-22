"""ToDo ファイルの残存チェック用スクリプト."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List

TODO_FILENAME_RE = re.compile(r"^[0-9]{8}-[A-Za-z0-9_-]+\.md$")
CHECKBOX_RE = re.compile(r"^(- \[(?: |x)\] .*)$", re.MULTILINE)
ROADMAP_ITEM_RE = re.compile(r"^(RM-\d{3})\s+.+$")
ANCHOR_TEMPLATE = '<a id="{anchor}"></a>'
BRANCH_RE = re.compile(r"^(feat|fix|chore|docs)/rm\d{3}-[a-z0-9][a-z0-9-]*$")


def list_todo_files(todo_dir: Path) -> List[Path]:
    return sorted(
        path
        for path in todo_dir.iterdir()
        if path.is_file() and TODO_FILENAME_RE.match(path.name)
    )


def parse_front_matter(content: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    in_front_matter = False
    for line in content.splitlines():
        stripped = line.strip()
        if not in_front_matter:
            if stripped == "---":
                in_front_matter = True
                continue
            if ":" not in line:
                break
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
            continue
        if stripped == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


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


def validate_roadmap_item(fields: Dict[str, str], roadmap_content: str) -> List[str]:
    issues: List[str] = []
    roadmap_item = fields.get("roadmap_item")
    if not roadmap_item:
        issues.append("front matter に roadmap_item がありません")
        return issues

    match = ROADMAP_ITEM_RE.match(roadmap_item)
    if not match:
        issues.append(f"roadmap_item が `RM-xxx テーマ名` 形式ではありません: {roadmap_item}")
        return issues

    item_code = match.group(1)
    anchor = ANCHOR_TEMPLATE.format(anchor=item_code.lower())
    if anchor not in roadmap_content:
        issues.append(f"docs/roadmap/roadmap.md に {item_code} のセクションが見つかりません")
    return issues


def lint_todo_file(path: Path, roadmap_content: str) -> List[str]:
    content = path.read_text(encoding="utf-8")
    issues = lint_todo_content(content)
    fields = parse_front_matter(content)
    issues.extend(validate_roadmap_item(fields, roadmap_content))
    branch = fields.get("関連ブランチ")
    if branch and branch != "未作成" and not BRANCH_RE.match(branch):
        issues.append(f"関連ブランチ が `prefix/rmxxx-slug` 形式ではありません: {branch}")
    roadmap_item = fields.get("roadmap_item")
    if roadmap_item:
        match = ROADMAP_ITEM_RE.match(roadmap_item)
        if match:
            code = match.group(1).lower()
            normalized = code.replace("-", "")
            name_lower = path.name.lower()
            if f"-{normalized}-" not in name_lower:
                issues.append(f"ファイル名に {normalized} を含めてください（例: YYYYMMDD-{normalized}-slug.md）")
    return issues


def lint_todo_directory(todo_dir: Path, roadmap_path: Path) -> Dict[Path, List[str]]:
    results: Dict[Path, List[str]] = {}
    if not roadmap_path.exists():
        print(f"ロードマップファイルが見つかりません: {roadmap_path}", file=sys.stderr)
        sys.exit(1)
    roadmap_content = roadmap_path.read_text(encoding="utf-8")
    for path in list_todo_files(todo_dir):
        issues = lint_todo_file(path, roadmap_content)
        if issues:
            results[path] = issues
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="ToDo 残存チェック")
    parser.add_argument(
        "--todo-dir", default="docs/todo", help="チェック対象の ToDo ディレクトリ"
    )
    parser.add_argument(
        "--roadmap", default="docs/roadmap/roadmap.md", help="ロードマップファイルのパス"
    )
    args = parser.parse_args()

    todo_dir = Path(args.todo_dir)
    if not todo_dir.exists():
        print(f"ToDo ディレクトリが見つかりません: {todo_dir}", file=sys.stderr)
        sys.exit(1)

    roadmap_path = Path(args.roadmap)

    results = lint_todo_directory(todo_dir, roadmap_path)
    if results:
        print("ToDo 残存チェックで問題を検出しました:\n")
        for path, issues in results.items():
            for issue in issues:
                print(f"- {path}: {issue}")
        sys.exit(1)

    print("ToDo 残存チェックに問題はありません。")


if __name__ == "__main__":
    main()
