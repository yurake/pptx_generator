#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pptx_generator.stages.shared.slides import build_slide_key


def _load_blueprint_slides(spec_path: Path) -> list[dict]:
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    blueprint = payload.get("blueprint")
    if not isinstance(blueprint, dict):
        return []
    slides = blueprint.get("slides")
    if not isinstance(slides, list):
        return []
    return [slide for slide in slides if isinstance(slide, dict)]


def main() -> None:
    parser = argparse.ArgumentParser(description="slide_inputs.md をテンプレート仕様から再生成する")
    parser.add_argument(
        "--template-spec",
        type=Path,
        default=Path(".pptx/template/template_spec.json"),
        help="template_spec.json のパス",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".pptx/slide_inputs.md"),
        help="slide_inputs.md の出力先",
    )
    args = parser.parse_args()

    spec_path = args.template_spec
    jobspec_path = None
    jobspec_env = os.environ.get("PPTX_JOBSPEC_PATH")
    if jobspec_env:
        jobspec_path = Path(jobspec_env).expanduser().resolve()

    if not spec_path.exists() and jobspec_path and jobspec_path.exists():
        jobspec_payload = json.loads(jobspec_path.read_text(encoding="utf-8"))
        meta = jobspec_payload.get("meta", {})
        tpl_spec_rel = meta.get("template_spec_path") if isinstance(meta, dict) else None
        if isinstance(tpl_spec_rel, str) and tpl_spec_rel.strip():
            candidate = (jobspec_path.parent / tpl_spec_rel).resolve()
            if candidate.exists():
                spec_path = candidate

    slides = _load_blueprint_slides(spec_path)
    if not slides:
        raise ValueError(f"blueprint slides が見つかりません: {spec_path}")

    lines = [
        "# Slide Inputs Manifest",
        "# 記法: <01_system-layout>: <data file path>",
        "# 例: 01_system-layout: samples/input/pitch.md",
        "",
    ]
    for index, slide in enumerate(slides, start=1):
        layout = slide.get("layout") if isinstance(slide.get("layout"), str) else None
        slide_id = slide.get("slide_id") if isinstance(slide.get("slide_id"), str) else None
        key = build_slide_key(index, layout, slide_id)
        lines.append(f"{key}: <data file path>")

    output_path = args.output
    if not output_path.is_absolute() and jobspec_path:
        output_path = (jobspec_path.parent.parent / "slide_inputs.md").resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
