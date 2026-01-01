from __future__ import annotations

from pathlib import Path
from typing import Iterable

import click

from pptx_generator.cli_hooks import (
    ExternalHookManager,
    extract_template_id_from_json_file,
    load_hooks_for_template_id,
)


def load_stage_hooks(spec_path: Path) -> tuple[ExternalHookManager | None, str | None]:
    """jobspec から template_id を抽出し、対応する HookManager を返す。"""

    template_id = extract_template_id_from_json_file(spec_path)

    hook_manager = load_hooks_for_template_id(template_id) if template_id else None
    return hook_manager, template_id


def run_stage_hook(
    stage: str,
    *,
    hook_manager: ExternalHookManager | None,
    template_id: str | None,
    stage_env: dict[str, str],
) -> bool:
    """ステージフックを実行し、既定処理を継続するか判定する。"""

    if not hook_manager:
        return False

    executed, continue_default = hook_manager.run_stage_hook(
        stage,
        env=stage_env,
    )
    if not executed:
        return False

    click.echo(f"[hooks] {stage} stage executed via external hook (template_id={template_id})")
    return not continue_default


def run_slide_hooks(
    stage: str,
    *,
    hook_manager: ExternalHookManager | None,
    stage_env: dict[str, str],
    slides: Iterable[object],
    continue_default_filter: bool,
) -> bool:
    """スライドフックを実行し、既定処理を継続するか判定する。"""

    if not hook_manager:
        return False

    return hook_manager.run_slide_hooks(
        stage,
        slides=slides,
        env=stage_env,
        continue_default_filter=continue_default_filter,
        allow_fallback_context=True,
    )


def run_post_stage_slide_hooks(
    stage: str,
    *,
    hook_manager: ExternalHookManager | None,
    template_id: str | None,
    base_stage_env: dict[str, str],
    generate_ready_path: Path,
    slide_context_loader,
) -> None:
    """ステージ完了後のスライドフックを実行する。"""

    if not hook_manager or not template_id:
        return

    stage_env_with_outputs = dict(base_stage_env)
    stage_env_with_outputs["PPTX_GENERATE_READY_PATH"] = str(generate_ready_path.resolve())
    contexts = slide_context_loader(generate_ready_path)
    hook_manager.run_slide_hooks(
        stage,
        slides=contexts,
        env=stage_env_with_outputs,
        continue_default_filter=True,
        allow_fallback_context=True,
    )


__all__ = [
    "load_stage_hooks",
    "run_stage_hook",
    "run_slide_hooks",
    "run_post_stage_slide_hooks",
]
