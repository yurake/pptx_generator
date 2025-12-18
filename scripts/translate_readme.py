#!/usr/bin/env python
"""
translate_readme.py

README.md（日本語）をソースとして、
README.en.md / README.zh.md を OpenAI で翻訳生成するスクリプト。

- --mode auto（default）:
    base-ref とのブロック差分だけ翻訳し、
    変更されたブロックのみ README.en.md / README.zh.md に反映する
- --mode full:
    README.md 全文を翻訳して en / zh を丸ごと生成し直す

GitHub Actions / ローカル両方で利用可能な設計。
"""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

SOURCE_PATH = Path("README.md")
TARGETS: List[Tuple[str, Path]] = [
    ("en", Path("README.en.md")),
    ("zh", Path("README.zh.md")),
]

Mode = Literal["auto", "full"]

LANG_DESC: Dict[str, str] = {
    "en": "natural, fluent technical English for software developers",
    "zh": "自然で読みやすい簡体字中国語（中国本土の開発者向け）",
}

SYSTEM_PROMPTS: Dict[str, str] = {
    "en": """\
You are a professional technical translator.
Translate the given Japanese Markdown block into natural, fluent technical English for software developers.

Requirements:
- Preserve the Markdown structure (headings, lists, code blocks, tables, links).
- Do NOT add explanations, comments, or extra sentences.
- Keep programming terminology and product/repository names unchanged.
- Only translate natural language text.
""",
    "zh": """\
You are a professional technical translator.
Translate the given Japanese Markdown block into natural and easy-to-read Simplified Chinese for software developers in Mainland China.

Requirements:
- Preserve the Markdown structure (headings, lists, code blocks, tables, links).
- Do NOT add explanations, comments, or extra sentences.
- Keep programming terminology and product/repository names unchanged.
- Only translate natural language text.
""",
}


@dataclass
class Block:
    """Markdown を「コードブロック / 通常ブロック」単位に分けるための構造体。"""
    lines: List[str]
    is_code: bool

    def text(self) -> str:
        return "".join(self.lines)


def split_markdown_blocks(text: str) -> List[Block]:
    """
    簡易な Markdown ブロック分割。
    - ``` で始まる行から ``` 行までを 1 つのコードブロックとして扱う
    - それ以外は、空行で区切られた「連続した非空行」を 1 ブロックとして扱う
    """
    lines = text.splitlines(keepends=True)
    blocks: List[Block] = []

    in_code = False
    current_lines: List[str] = []
    current_is_code = False

    def flush_block():
        nonlocal current_lines, current_is_code
        if current_lines:
            blocks.append(Block(lines=list(current_lines),
                          is_code=current_is_code))
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


def join_blocks(blocks: List[Block]) -> str:
    """Block のリストをテキストに戻す。"""
    return "".join(b.text() for b in blocks)


def get_base_readme(base_ref: str) -> Optional[str]:
    """
    git show <base_ref>:README.md を実行して、その内容を取得する。
    失敗した場合は None を返す。
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{base_ref}:README.md"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None

    return result.stdout


def create_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def translate_block(client: OpenAI, lang_code: str, block: Block) -> str:
    """
    単一ブロックを翻訳する。
    コードブロックは翻訳しないでそのまま返す。
    """
    if block.is_code:
        return block.text()

    content = block.text()
    if not content.strip():
        return content

    system_prompt = SYSTEM_PROMPTS[lang_code]

    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    )

    translated = resp.choices[0].message.content or ""

    original_trailing_newlines = len(content) - len(content.rstrip("\n"))
    if original_trailing_newlines <= 0:
        original_trailing_newlines = 1

    translated = translated.rstrip("\n") + ("\n" * original_trailing_newlines)
    return translated


def auto_translate(
    client: OpenAI,
    base_ref: Optional[str],
) -> None:
    """
    --mode auto 用。
    base_ref から README.md の旧版を取得し、ブロック単位で差分更新する。
    - base 的な README が取得できない
    - ブロック数が大きく変わる
    - en/zh 既存ブロック数が合わない
    といった場合は安全側で full 翻訳にフォールバックする。
    """
    if not SOURCE_PATH.exists():
        raise FileNotFoundError("README.md not found")

    current_text = SOURCE_PATH.read_text(encoding="utf-8")
    current_blocks = split_markdown_blocks(current_text)

    if base_ref is None:
        raise ValueError("--mode auto requires --base-ref to be specified")

    base_text = get_base_readme(base_ref)
    if base_text is None:
        full_translate(client)
        return

    base_blocks = split_markdown_blocks(base_text)

    if len(base_blocks) != len(current_blocks):
        raise RuntimeError(
            f"Block count mismatch between base and current README: "
            f"base={len(base_blocks)}, current={len(current_blocks)}. "
            "Adjust README.md so block counts match, then rerun."
        )

    existing_translated: Dict[str, List[Block]] = {}
    for lang_code, path in TARGETS:
        if not path.exists():
            raise RuntimeError(
                f"{path} is missing. Ensure translated README exists before running auto mode."
            )
        text = path.read_text(encoding="utf-8")
        blocks = split_markdown_blocks(text)
        if len(blocks) != len(current_blocks):
            raise RuntimeError(
                f"Block count mismatch for {path}: "
                f"{len(blocks)} (translated) vs {len(current_blocks)} (current README). "
                "Align block structure and rerun."
            )
        existing_translated[lang_code] = blocks

    changed_indices: List[int] = []
    for i, (base_b, cur_b) in enumerate(zip(base_blocks, current_blocks)):
        if base_b.text() != cur_b.text():
            changed_indices.append(i)

    if not changed_indices:
        print("No block-level changes detected in README.md. Skip translation.")
        return

    print(f"Changed blocks: {changed_indices}")

    for lang_code, target_path in TARGETS:
        new_blocks: List[Block] = []
        for i, cur_block in enumerate(current_blocks):
            if i in changed_indices:
                translated_text = translate_block(client, lang_code, cur_block)
                new_blocks.append(Block(lines=translated_text.splitlines(keepends=True),
                                        is_code=cur_block.is_code))
            else:
                prev_block = existing_translated[lang_code][i]
                new_blocks.append(prev_block)

        new_text = join_blocks(new_blocks)
        target_path.write_text(new_text, encoding="utf-8")
        print(f"Updated {target_path} (auto mode)")


def full_translate(client: OpenAI) -> None:
    """
    --mode full 用。
    README.md 全体をブロック分割し、すべてのブロックを翻訳して en/zh を丸ごと更新する。
    """
    if not SOURCE_PATH.exists():
        raise FileNotFoundError("README.md not found")

    src_text = SOURCE_PATH.read_text(encoding="utf-8")
    src_blocks = split_markdown_blocks(src_text)

    for lang_code, target_path in TARGETS:
        new_blocks: List[Block] = []
        for block in src_blocks:
            translated_text = translate_block(client, lang_code, block)
            new_blocks.append(
                Block(
                    lines=translated_text.splitlines(keepends=True),
                    is_code=block.is_code,
                )
            )
        new_text = join_blocks(new_blocks)
        target_path.write_text(new_text, encoding="utf-8")
        print(f"Updated {target_path} (full mode)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate README.md (Japanese) into README.en.md and README.zh.md using OpenAI."
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "full"],
        default="auto",
        help=(
            "Translation mode. "
            "'auto' (default): translate only changed blocks based on base-ref. "
            "'full': translate the entire README.md."
        ),
    )
    parser.add_argument(
        "--base-ref",
        help=(
            "Base git ref/commit for diff when using --mode auto. "
            "If omitted in auto mode, 'HEAD^' is used as a best-effort default."
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    mode: Mode = args.mode
    base_ref: Optional[str] = args.base_ref

    client = create_openai_client()

    if mode == "full":
        full_translate(client)
    else:
        auto_translate(client, base_ref)


if __name__ == "__main__":
    main()
