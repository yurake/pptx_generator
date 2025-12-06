from __future__ import annotations

import logging
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import app


def test_cli_initializes_file_logging() -> None:
    runner = CliRunner()
    root_logger = logging.getLogger()
    root_level = root_logger.level
    original_root_handlers = list(root_logger.handlers)

    llm_logger = logging.getLogger("pptx_generator.slide_ai.llm")
    llm_level = llm_logger.level
    llm_propagate = llm_logger.propagate
    original_llm_handlers = list(llm_logger.handlers)
    original_llm_filters = list(llm_logger.filters)

    openai_logger = logging.getLogger("openai")
    openai_level = openai_logger.level

    try:
        with runner.isolated_filesystem():
            callback = app.callback
            assert callback is not None
            callback(verbose=False, debug=False)

            new_file_handlers = [
                handler
                for handler in root_logger.handlers
                if handler not in original_root_handlers and isinstance(handler, logging.FileHandler)
            ]
            assert new_file_handlers

            record = logging.LogRecord(
                name="pptx_generator.cli",
                level=logging.WARNING,
                pathname=__file__,
                lineno=0,
                msg="test log entry",
                args=(),
                exc_info=None,
            )

            for handler in new_file_handlers:
                handler.handle(record)
                if hasattr(handler, "flush"):
                    handler.flush()
                log_path = Path(handler.baseFilename)
                assert log_path.exists()
                log_text = log_path.read_text(encoding="utf-8")
                assert "test log entry" in log_text
    finally:
        for handler in list(root_logger.handlers):
            if handler not in original_root_handlers:
                root_logger.removeHandler(handler)
                handler.close()
        root_logger.setLevel(root_level)

        for handler in list(llm_logger.handlers):
            if handler not in original_llm_handlers:
                llm_logger.removeHandler(handler)
                handler.close()
        for log_filter in list(llm_logger.filters):
            if log_filter not in original_llm_filters:
                llm_logger.removeFilter(log_filter)
        llm_logger.setLevel(llm_level)
        llm_logger.propagate = llm_propagate

        openai_logger.setLevel(openai_level)
