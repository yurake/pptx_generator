#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path
from typing import Dict, Tuple

FRONT_MATTER_RE = re.compile(r"^---\n(?P<body>.*?)\n---\n", re.DOTALL)


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        return handle.read()


def write_text(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(content)


def parse_front_matter(content: str) -> Dict[str, str]:
    match = FRONT_MATTER_RE.match(content)
    fields: Dict[str, str] = {}
    if not match:
        return fields
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def mark_all_tasks_complete(content: str) -> Tuple[str, bool]:
    lines = content.splitlines()
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("- [ ]"):
            lines[index] = line.replace("- [ ]", "- [x]", 1)
            updated = True
    new_content = "\n".join(lines)
    if content.endswith("\n"):
        new_content += "\n"
    return new_content, updated


def update_pr_memo(content: str, pr_number: int, pr_url: str, date_str: str) -> Tuple[str, bool]:
    lines = content.splitlines()
    memo_line = f"  - メモ: PR #{pr_number} {pr_url}（{date_str} 完了）"
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("- [x] PR 作成"):
            memo_index = index + 1
            if memo_index < len(lines) and lines[memo_index].startswith("  - メモ:"):
                if lines[memo_index] != memo_line:
                    lines[memo_index] = memo_line
                    updated = True
            else:
                lines.insert(memo_index, memo_line)
                updated = True
            break
    new_content = "\n".join(lines)
    if content.endswith("\n"):
        new_content += "\n"
    return new_content, updated


def archive_todo(todo_path: Path, archive_dir: Path, dry_run: bool) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    destination = archive_dir / todo_path.name
    if dry_run:
        return destination
    shutil.move(str(todo_path), destination)
    return destination


def split_roadmap_item(roadmap_item: str) -> Tuple[str, str]:
    match = re.match(r"(RM-\d{3})\s*(.*)", roadmap_item)
    if not match:
        raise ValueError("roadmap_item must follow 'RM-xxx テーマ名'")
    return match.group(1), match.group(2).strip()


def update_roadmap(
    roadmap_path: Path,
    roadmap_item: str,
    todo_filename: str,
    pr_number: int,
    pr_url: str,
    date_str: str,
    dry_run: bool,
) -> bool:
    content = read_text(roadmap_path)
    item_code, _ = split_roadmap_item(roadmap_item)
    anchor = item_code.lower()
    block_pattern = re.compile(
        rf"(<a id=\"{anchor}\"></a>\n### {item_code}\b.*?)(?=\n<a id=\"rm-\d{{3}}\">|\n## |\Z)",
        re.DOTALL,
    )
    match = block_pattern.search(content)
    if not match:
        raise ValueError(f"ロードマップに {item_code} のエントリが見つかりません")

    block = match.group(1)
    block = block.replace(f"docs/todo/{todo_filename}", f"docs/todo/archive/{todo_filename}")
    block = block.replace(f"(../todo/{todo_filename})", f"(../todo/archive/{todo_filename})")
    block = re.sub(r"- 状況:.*", f"- 状況: 完了（{date_str} 更新）", block, count=1)
    block = re.sub(r"- 次のアクション:.*\n?", "", block)

    achievement_line = f"- 成果: PR #{pr_number} {pr_url}"
    if "成果:" not in block:
        block = block.rstrip() + "\n" + achievement_line + "\n"
    else:
        block = re.sub(r"- 成果:.*", achievement_line, block, count=1)

    block = re.sub(r"\n{3,}", "\n\n", block).strip() + "\n"

    updated_content = content[: match.start()] + content[match.end() :]

    completed_section_pattern = re.compile(r"(## 完了テーマ\n)")
    completed_match = completed_section_pattern.search(updated_content)
    if not completed_match:
        raise ValueError("ロードマップに完了テーマセクションが存在しません")

    insertion_point = completed_match.end()
    updated_content = (
        updated_content[:insertion_point]
        + "\n"
        + block
        + "\n"
        + updated_content[insertion_point:]
    )
    updated_content = re.sub(r"\n{3,}", "\n\n", updated_content).rstrip() + "\n"

    if dry_run:
        return content != updated_content
    write_text(roadmap_path, updated_content)
    return content != updated_content


def process_todo(todo_path: Path, archive_dir: Path, pr_number: int, pr_url: str, dry_run: bool) -> Tuple[Path, Dict[str, str]]:
    content = read_text(todo_path)
    fields = parse_front_matter(content)
    if "roadmap_item" not in fields:
        raise ValueError(f"{todo_path} に roadmap_item がありません")

    content, _ = mark_all_tasks_complete(content)
    today = dt.date.today().isoformat()
    content, _ = update_pr_memo(content, pr_number, pr_url, today)

    if not dry_run:
        write_text(todo_path, content)

    archived_path = archive_todo(todo_path, archive_dir, dry_run)
    return archived_path, fields


def main() -> None:
    parser = argparse.ArgumentParser(description="ToDo / ロードマップ自動完了スクリプト")
    parser.add_argument("--todo", action="append", required=True, help="対象の ToDo ファイルパス")
    parser.add_argument("--pr-number", type=int, required=True, help="マージ済み PR の番号")
    parser.add_argument("--pr-url", required=True, help="マージ済み PR の URL")
    parser.add_argument("--roadmap", default="docs/roadmap/README.md", help="ロードマップファイルのパス")
    parser.add_argument("--archive-dir", default="docs/todo/archive", help="アーカイブ先ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="ファイルを更新せず差分のみ出力")
    args = parser.parse_args()

    archive_dir = Path(args.archive_dir)
    roadmap_path = Path(args.roadmap)

    results = []
    for todo in args.todo:
        todo_path = Path(todo)
        if not todo_path.exists():
            raise FileNotFoundError(f"{todo} が見つかりません")
        archived_path, fields = process_todo(todo_path, archive_dir, args.pr_number, args.pr_url, args.dry_run)
        results.append((archived_path, fields))

    for archived_path, fields in results:
        roadmap_item = fields["roadmap_item"]
        update_roadmap(
            roadmap_path=roadmap_path,
            roadmap_item=roadmap_item,
            todo_filename=archived_path.name,
            pr_number=args.pr_number,
            pr_url=args.pr_url,
            date_str=dt.date.today().isoformat(),
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
