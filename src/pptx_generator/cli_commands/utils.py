from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Callable

import click


def handle_command_error(exc: Exception, *, default_message: str) -> None:
    message = str(exc) or default_message
    if message:
        click.echo(message, err=True)


def draft_common_options(
    *,
    default_appendix_limit: int,
    default_prepare_cards_path,
    prepare_cards_exists: bool,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @click.option(
            "--target-length",
            type=click.IntRange(1, None),
            default=None,
            help="スライド枚数の目標値",
        )
        @click.option(
            "--structure",
            "structure_pattern",
            type=str,
            default=None,
            help="ドラフト構成のパターン名",
        )
        @click.option(
            "--appendix-limit",
            type=click.IntRange(0, None),
            default=default_appendix_limit,
            show_default=True,
            help="付録の最大枚数",
        )
        @click.option(
            "--analysis-summary",
            "analysis_summary_path",
            type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
            default=None,
            help="分析サマリ JSON のパス",
        )
        @click.option(
            "--show-layout-reasons",
            is_flag=True,
            default=False,
            help="レイアウト推奨理由を表示する",
        )
        @click.option(
            "--prepare-cards",
            type=click.Path(exists=prepare_cards_exists, dir_okay=False, readable=True, path_type=Path),
            default=default_prepare_cards_path,
            show_default=True,
            help="prepare_card.json のパス",
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = ["draft_common_options", "handle_command_error"]
