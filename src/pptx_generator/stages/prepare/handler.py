from __future__ import annotations

from pathlib import Path
from typing import Callable

from .errors import PrepareCommandError
from .models import PrepareCommandConfig, PrepareCommandResult

SLIDE_INPUTS_FILENAME = Path("slide_inputs.md")


def run_prepare_command(
    config: PrepareCommandConfig,
    *,
    dump_json: Callable[[Path, object], None],
) -> PrepareCommandResult:
    raise PrepareCommandError("prepare コマンドは廃止されました", exit_code=2)


__all__ = [
    "PrepareCommandConfig",
    "PrepareCommandError",
    "PrepareCommandResult",
    "SLIDE_INPUTS_FILENAME",
    "run_prepare_command",
]
