from __future__ import annotations

from contextlib import contextmanager
import sys
import os
from pathlib import Path
from typing import Iterable

from pptx_generator.stages.shared.slides import slide_contexts_from_generate_ready


@contextmanager
def _temporary_env(values: dict[str, str]) -> Iterable[None]:
    original: dict[str, str | None] = {}
    for key, value in values.items():
        original[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, previous in original.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _base_env(*, stage: str, output_dir: Path, context_path: Path | None) -> dict[str, str]:
    env = {
        "PPTX_STAGE": stage,
        "PPTX_OUTPUT_DIR": str(output_dir.resolve()),
    }
    if context_path is not None:
        env["PPTX_CONTEXT_PATH"] = str(context_path.resolve())
    return env


def run_prepare_scripts(
    *,
    output_dir: Path,
    jobspec_path: Path | None,
    prepare_inputs: list[str],
    context_path: Path | None,
) -> None:
    env = _base_env(stage="prepare", output_dir=output_dir, context_path=context_path)
    env["PPTX_PREPARE_OUTPUT_DIR"] = str(output_dir.resolve())
    env["PPTX_MODE"] = "static"
    if jobspec_path is not None:
        env["PPTX_JOBSPEC_PATH"] = str(jobspec_path.resolve())
    if prepare_inputs:
        env["PPTX_PREPARE_INPUTS"] = "\n".join(prepare_inputs)
        env.setdefault("JRI_EXCEL_SOURCE", prepare_inputs[0])

    with _temporary_env(env):
        from pptx_generator.executive_board.overview import stage02_prepare as overview
        from pptx_generator.executive_board.system import stage02_prepare as system
        from pptx_generator.executive_board.cost import stage02_prepare as cost
        from pptx_generator.executive_board.schedule import stage02_prepare as schedule
        from pptx_generator.executive_board.organization import stage02_prepare as organization
        from pptx_generator.executive_board.personnel import stage02_prepare as personnel

        overview.main()
        system.main()
        cost.main()
        schedule.main()
        organization.main()
        personnel.main()


def run_compose_scripts(
    *,
    generate_ready_path: Path,
    output_dir: Path,
    context_path: Path | None,
) -> None:
    env = _base_env(stage="compose", output_dir=output_dir, context_path=context_path)
    env["PPTX_GENERATE_READY_PATH"] = str(generate_ready_path.resolve())

    with _temporary_env(env):
        from pptx_generator.executive_board.overview import generate_ready_from_input_sample
        from pptx_generator.executive_board.system import generate_ready_from_requirements

        original_argv = sys.argv
        try:
            sys.argv = [__file__]
            generate_ready_from_input_sample.main()
            sys.argv = [__file__]
            generate_ready_from_requirements.main()
        finally:
            sys.argv = original_argv


def run_gen_scripts(
    *,
    generate_ready_path: Path,
    output_dir: Path,
    pptx_name: str,
    context_path: Path | None,
) -> None:
    env = _base_env(stage="gen", output_dir=output_dir, context_path=context_path)
    env["PPTX_GENERATE_READY_PATH"] = str(generate_ready_path.resolve())
    env["PPTX_PPTX_NAME"] = pptx_name

    contexts = slide_contexts_from_generate_ready(generate_ready_path)
    slide_index_map = {ctx.key: ctx.index for ctx in contexts}

    script_map = [
        ("01_project-background-layout-01", "overview"),
        ("02_3-system-layout-02", "system"),
        ("03_2-03", "cost"),
        ("04_system-layout-04", "schedule"),
        ("05_1-system-layout-05", "organization"),
        ("06_2-system-layout-06", "personnel"),
    ]

    with _temporary_env(env):
        from pptx_generator.executive_board.overview import stage04_gen as overview
        from pptx_generator.executive_board.system import stage04_gen as system
        from pptx_generator.executive_board.cost import stage04_gen as cost
        from pptx_generator.executive_board.schedule import stage04_gen as schedule
        from pptx_generator.executive_board.organization import stage04_gen as organization
        from pptx_generator.executive_board.personnel import stage04_gen as personnel

        runners = {
            "overview": overview.main,
            "system": system.main,
            "cost": cost.main,
            "schedule": schedule.main,
            "organization": organization.main,
            "personnel": personnel.main,
        }

        for key, name in script_map:
            slide_index = slide_index_map.get(key)
            if slide_index is not None:
                os.environ["PPTX_SLIDE_PAGE_NO"] = str(slide_index)
                os.environ["PPTX_SLIDE_INDEX"] = str(slide_index)
            else:
                os.environ.pop("PPTX_SLIDE_PAGE_NO", None)
                os.environ.pop("PPTX_SLIDE_INDEX", None)
            runners[name]()
