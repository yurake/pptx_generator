from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import click


def echo_command_errors(message: str, errors: list[dict[str, Any]] | None) -> None:
    click.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    click.echo(formatted, err=True)


def handle_command_error(exc: Exception, *, default_message: str) -> None:
    """CLI コマンド例外を共通の形式で標準エラー出力へ表示する。"""

    message = str(exc)
    errors = getattr(exc, "errors", None)
    if errors:
        echo_command_errors(message or default_message, errors)
    elif message:
        click.echo(message, err=True)


def apply_options(options: Iterable[Callable[[Callable], Callable]]) -> Callable[[Callable], Callable]:
    """click.option 群をまとめて適用するヘルパー。"""

    def decorator(func: Callable) -> Callable:
        for option in reversed(list(options)):
            func = option(func)
        return func

    return decorator


def draft_common_options(
    *,
    default_appendix_limit: int,
    default_prepare_cards_path: Path,
    prepare_cards_exists: bool,
) -> Callable[[Callable], Callable]:
    """compose/outline 向けの共通オプションを付与するデコレータ。"""

    return apply_options(
        [
            click.option(
                "--target-length",
                type=int,
                default=None,
                help="目標スライド枚数",
            ),
            click.option(
                "--structure-pattern",
                type=str,
                default=None,
                help="章構成パターン名",
            ),
            click.option(
                "--appendix-limit",
                type=int,
                default=default_appendix_limit,
                show_default=True,
                help="付録枚数の上限",
            ),
            click.option(
                "--import-analysis",
                "analysis_summary_path",
                type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
                default=None,
                help="analysis_summary.json のパス",
            ),
            click.option(
                "--show-layout-reasons",
                is_flag=True,
                default=False,
                help="layout_hint 候補のスコア内訳を表示する",
            ),
            click.option(
                "--prepare-cards",
                type=click.Path(
                    exists=prepare_cards_exists,
                    dir_okay=False,
                    readable=True,
                    path_type=Path,
                ),
                default=default_prepare_cards_path,
                show_default=True,
                help="stage 2 の prepare_card.json",
            ),
        ]
    )


__all__ = [
    "echo_command_errors",
    "handle_command_error",
    "apply_options",
    "draft_common_options",
]
