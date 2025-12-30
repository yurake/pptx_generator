from __future__ import annotations

import logging

from pptx_generator.logging import LoggingContextFilter, ensure_stream_handler, ensure_rotating_file_handler


def test_ensure_handlers_adds_context_filter(tmp_path) -> None:
    logger = logging.getLogger("pptx_generator.test.logging_utils")
    logger.handlers.clear()
    logger.filters.clear()

    ensure_stream_handler(logger, level=logging.INFO)
    ensure_rotating_file_handler(logger, file_path=tmp_path / "out.log", level=logging.INFO)

    assert any(isinstance(f, LoggingContextFilter) for f in logger.filters)
    for handler in logger.handlers:
        assert any(isinstance(f, LoggingContextFilter) for f in handler.filters)
