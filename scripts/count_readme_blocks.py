#!/usr/bin/env python3
"""README 系 Markdown ファイルのブロック数を確認するユーティリティ。"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

Block = Tuple[bool, List[str]]  # (is_code, lines)


def split_markdown_blocks(text: str) -> List[Block]:
    """`translate_readme.py` と同じロジックで Markdown をブロック分割する。"""
    lines = text.splitlines(keepends=True)
    blocks: List[Block] = []

    in_code = False
    current_lines: List[str] = []
    current_is_code = False

    def flush_block() -> None:
        nonlocal current_lines, current_is_code
        if current_lines:
            blocks.append((current_is_code, list(current_lines)))
            current_lines = []
            current_is_code = False

    for line in lines:
        if line.strip().startswith("```"):
            if not in_code:
                flush_block()
                in_code = True
                current_is_code = True
                current_lines.append(line)
            else:
                current_lines.append(line)
                flush_block()
                in_code = False
                current_is_code = False
            continue

        if in_code:
            current_lines.append(line)
        else:
            if line.strip() == "":
                current_lines.append(line)
                flush_block()
            else:
                current_lines.append(line)

    flush_block()
    return blocks


def summarize_block(block: Block) -> str:
    is_code, lines = block
    kind = "code" if is_code else "text"
    preview_lines = "".join(lines).strip().splitlines()
    head = preview_lines[0] if preview_lines else "(empty)"
    return f"{kind}: {head}"


def main(paths: List[str]) -> None:
    summaries = []
    detailed_info = []

    for path_str in paths:
        path = Path(path_str)
        text = path.read_text(encoding="utf-8")
        blocks = split_markdown_blocks(text)
        code_count = sum(1 for block in blocks if block[0])
        text_count = len(blocks) - code_count
        summaries.append(
            f"- {path}: total {len(blocks)} blocks (text {text_count}, code {code_count})"
        )

        per_file_lines = [f"{path}: {len(blocks)} blocks"]
        per_file_lines.extend(
            f"  [{idx:02d}] {summarize_block(block)}" for idx, block in enumerate(blocks)
        )
        detailed_info.append("\n".join(per_file_lines))

    if summaries:
        print("Summary:")
        print("\n".join(summaries))
        print()

    for section in detailed_info:
        print(section)
        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/count_readme_blocks.py <path> [<path> ...]")
        sys.exit(1)

    main(sys.argv[1:])
