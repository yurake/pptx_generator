from __future__ import annotations

from collections.abc import Iterable
from typing import Sequence


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_lines_preserve_blank(text: str) -> list[str]:
    normalized = normalize_newlines(text)
    return normalized.split("\n")


def strip_lines_preserve_blank(lines: Iterable[str]) -> list[str]:
    output: list[str] = []
    for line in lines:
        stripped = str(line).strip()
        if stripped:
            output.append(stripped)
        else:
            output.append("")
    return output


def split_text_preserve_blank(text: str | None) -> list[str]:
    if not isinstance(text, str):
        return []
    return strip_lines_preserve_blank(split_lines_preserve_blank(text))


def normalize_line_list_preserve_blank(lines: Sequence[str] | None) -> list[str]:
    if not lines:
        return []
    return strip_lines_preserve_blank(lines)
