from __future__ import annotations

import click
from click.testing import CliRunner

from pptx_generator.cli_commands.utils import (
    apply_options,
    draft_common_options,
    handle_command_error,
)


class DummyError(Exception):
    def __init__(self, message: str = "", errors=None) -> None:  # noqa: ANN001
        super().__init__(message)
        self.errors = errors


def test_handle_command_error_uses_default_message_when_empty(capsys) -> None:
    exc = DummyError()

    handle_command_error(exc, default_message="fallback message")

    err = capsys.readouterr().err
    assert "fallback message" in err


def test_handle_command_error_outputs_json_errors(capsys) -> None:
    exc = DummyError("boom", errors=[{"msg": "x"}])

    handle_command_error(exc, default_message="ignored")

    err = capsys.readouterr().err
    assert "boom" in err
    assert '"msg": "x"' in err


def test_handle_command_error_outputs_default_when_no_message_and_no_errors(capsys) -> None:
    exc = DummyError("")

    handle_command_error(exc, default_message="fallback")

    err = capsys.readouterr().err
    assert "fallback" in err


def test_handle_command_error_outputs_default_when_errors_empty(capsys) -> None:
    exc = DummyError("", errors=[])

    handle_command_error(exc, default_message="empty-errors")

    err = capsys.readouterr().err
    assert "empty-errors" in err


def test_apply_options_preserves_option_order() -> None:
    opt_order: list[str] = []

    def record_order(name: str):  # noqa: ANN001
        def callback(ctx, param, value):  # noqa: ANN001, ARG001
            opt_order.append(name)
            return value

        return callback

    options = [
        click.option("--first", callback=record_order("first"), default="a"),
        click.option("--second", callback=record_order("second"), default="b"),
    ]

    @click.command()
    @apply_options(options)
    def cmd(first, second):  # noqa: ANN001
        click.echo(f"{first}-{second}")

    result = CliRunner().invoke(cmd, ["--first", "x", "--second", "y"])
    assert result.exit_code == 0
    assert "x-y" in result.output
    assert opt_order == ["first", "second"]


def test_draft_common_options_allows_missing_prepare_cards(tmp_path) -> None:
    default_prepare = tmp_path / "missing" / "prepare_card.json"
    captured = {}

    @click.command()
    @draft_common_options(
        default_appendix_limit=5,
        default_prepare_cards_path=default_prepare,
        prepare_cards_exists=False,
    )
    def cmd(**kwargs):  # noqa: ANN003
        captured.update(kwargs)

    result = CliRunner().invoke(cmd, ["--appendix-limit", "-1"])
    assert result.exit_code == 0
    assert captured["appendix_limit"] == -1
    assert captured["prepare_cards"] == default_prepare
