from __future__ import annotations

import logging
from typing import Iterable, Tuple

import pytest

from pptx_generator.cli_handlers.common import determine_log_level


def _extract_messages(logs: Iterable[Tuple[int, str]]) -> list[str]:
    return [message for _, message in logs]


def test_determine_log_level_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_LOG", raising=False)
    monkeypatch.setenv("LOG_LEVEL", "info")

    level, logs = determine_log_level(verbose=False, debug=False)

    assert level == logging.INFO
    assert logs == []


def test_determine_log_level_invalid_env_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "loud")

    level, logs = determine_log_level(verbose=False, debug=False)

    assert level == logging.WARNING
    messages = _extract_messages(logs)
    assert any("LOG_LEVEL='loud'" in message for message in messages)
