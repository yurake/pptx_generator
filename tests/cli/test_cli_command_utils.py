from __future__ import annotations

from pptx_generator.cli_commands.utils import handle_command_error


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
