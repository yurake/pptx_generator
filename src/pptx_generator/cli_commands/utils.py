from __future__ import annotations

import json
from typing import Any

import click


def echo_command_errors(message: str, errors: list[dict[str, Any]] | None) -> None:
    click.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    click.echo(formatted, err=True)


__all__ = ["echo_command_errors"]
