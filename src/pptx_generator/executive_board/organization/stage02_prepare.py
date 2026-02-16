#!/usr/bin/env python3
"""Stage2 hook for organization: parse markdown to JSON for compose/gen."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.stage_shared import load_context, persist_context, resolve_input_path, resolve_local_path  # noqa: E402


def _configure_sys_path() -> None:
    src_dir = Path(__file__).resolve().parents[3] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    organization_dir = Path(__file__).resolve().parent
    if str(organization_dir) not in sys.path:
        sys.path.insert(0, str(organization_dir))


_configure_sys_path()

from organization_parser import (  # noqa: E402
    parse_organization_markdown,
    save_organization_json,
)


DEFAULT_MD = Path(__file__).resolve().parents[1] / "input/organization.md"
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[3] / "templates/organization.pptx"


def _resolve_template_path(context: dict[str, str | Path]) -> Path:
    candidates: list[str | Path] = []
    env_template = os.environ.get("PPTX_TEMPLATE_PATH")
    if isinstance(env_template, str) and env_template.strip():
        candidates.append(env_template.strip())
    if context.get("template_path"):
        candidates.append(context["template_path"])
    candidates.append(DEFAULT_TEMPLATE)

    for candidate in candidates:
        resolved = resolve_local_path(str(candidate), Path(__file__).resolve().parent)
        if resolved.exists():
            context["template_path"] = str(resolved)
            return resolved

    raise FileNotFoundError("Template PPTX not found. Provide PPTX_TEMPLATE_PATH or place templates/organization.pptx.")


def _resolve_md(context: dict[str, str]) -> Path:
    return resolve_input_path(
        env_var="PPTX_ORGANIZATION_MD",
        inputs_key="organization_md_path",
        context=context,
    )


def main(argv: list[str] | None = None) -> int:
    layout_mode = os.environ.get("PPTX_MODE", "").lower()
    if layout_mode and layout_mode != "static":
        return 0

    parser = argparse.ArgumentParser(description="organization prepare hook for executive_board")
    parser.add_argument("--md", help="組織図Markdownのパス (PPTX_ORGANIZATION_MD より優先)")
    parser.add_argument("--output", help="出力ディレクトリ (PPTX_PREPARE_OUTPUT_DIR より優先)")
    args = parser.parse_args(argv)

    context = load_context()
    _resolve_template_path(context)

    md_path = Path(args.md).expanduser().resolve() if args.md else _resolve_md(context)
    if not md_path.exists():
        raise FileNotFoundError(f"organization markdown not found: {md_path}")

    output_dir_env = os.environ.get("PPTX_PREPARE_OUTPUT_DIR")
    output_dir = Path(args.output).expanduser() if args.output else Path(output_dir_env) if output_dir_env else Path(".pptx/prepare")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    chart = parse_organization_markdown(md_path)
    json_path = output_dir / "organization_data.json"
    save_organization_json(chart, json_path)

    context.update(
        {
            "organization_md_path": str(md_path),
            "organization_json_path": str(json_path),
            "organization_layout": os.environ.get("PPTX_ORGANIZATION_LAYOUT", "System_layout"),
        }
    )
    persist_context(context)

    print(f"[stage02_prepare] organization JSON -> {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
