import logging
import sys
from logging import Handler
from logging.handlers import RotatingFileHandler

import pytest

from pptx_generator.api.logging_config import configure_api_logging
from pptx_generator.cli_handlers.common import configure_file_logging, configure_llm_logger


@pytest.fixture
def _restore_logging():
    """ロガー状態をテスト前後でリセットする。"""

    def _snapshot(logger_name: str):
        logger = logging.getLogger(logger_name)
        return logger, list(logger.handlers), logger.level, logger.propagate

    snapshots = [
        _snapshot(""),
        _snapshot("pptx_generator"),
        _snapshot("pptx_generator.api"),
        _snapshot("pptx_generator.slide_ai.llm"),
    ]

    for logger, handlers, _, _ in snapshots:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)
        logger.propagate = True

    yield

    for logger, handlers, level, propagate in snapshots:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        for handler in handlers:
            logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = propagate


def _count_handlers(logger: logging.Logger, handler_type: type[Handler]) -> int:
    return sum(isinstance(h, handler_type) for h in logger.handlers)


def test_configure_file_logging_sets_stdout_and_rotating(tmp_path, _restore_logging):
    root = logging.getLogger()
    configure_file_logging(log_dir=tmp_path)

    assert _count_handlers(root, RotatingFileHandler) == 1
    assert any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers)

    rotating = next(h for h in root.handlers if isinstance(h, RotatingFileHandler))
    assert getattr(rotating, "baseFilename", "") == str(tmp_path / "out.log")
    assert rotating.maxBytes == 10 * 1024 * 1024
    assert rotating.backupCount == 5


def test_configure_llm_logger_uses_stdout_and_rotating(tmp_path, _restore_logging):
    logger = logging.getLogger("pptx_generator.slide_ai.llm")
    configure_llm_logger(log_dir=tmp_path)

    assert _count_handlers(logger, RotatingFileHandler) == 1
    assert any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in logger.handlers)

    rotating = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
    assert getattr(rotating, "baseFilename", "") == str(tmp_path / "out.log")
    assert rotating.maxBytes == 10 * 1024 * 1024
    assert rotating.backupCount == 5

    stream = next(h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler))
    assert getattr(stream, "stream", None) is sys.stdout


def test_llm_logger_does_not_emit_prompt_body(tmp_path, caplog, _restore_logging):
    logger = logging.getLogger("pptx_generator.slide_ai.llm")
    configure_llm_logger(log_dir=tmp_path)

    secret_prompt = "THIS_IS_SECRET_PROMPT"
    secret_response = "THIS_IS_SECRET_RESPONSE"

    with caplog.at_level(logging.INFO, logger="pptx_generator.slide_ai.llm"):
        logger.info(
            "llm call",
            extra={
                "slide_id": "s1",
                "card_id": "c1",
                "model": "gpt",
                "intent": "draft",
                "warnings": "none",
                "prompt_len": len(secret_prompt),
                "response_len": len(secret_response),
                "truncated": False,
            },
        )

    # メッセージにプロンプト/レスポンス本文が含まれないことを確認
    assert secret_prompt not in caplog.text
    assert secret_response not in caplog.text


def test_configure_api_logging_uses_stdout_and_rotating(tmp_path, _restore_logging, monkeypatch):
    monkeypatch.chdir(tmp_path)
    api_logger = configure_api_logging("INFO")

    assert _count_handlers(api_logger, RotatingFileHandler) == 1
    assert any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in api_logger.handlers)

    rotating = next(h for h in api_logger.handlers if isinstance(h, RotatingFileHandler))
    assert getattr(rotating, "baseFilename", "").endswith("logs/out.log")
    assert rotating.maxBytes == 10 * 1024 * 1024
    assert rotating.backupCount == 5

    stream = next(h for h in api_logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler))
    assert getattr(stream, "stream", None) is sys.stdout

    # configure_api_logging attaches handlers to pptx_generator root when absent
    pg_logger = logging.getLogger("pptx_generator")
    assert _count_handlers(pg_logger, RotatingFileHandler) == 1
    assert any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in pg_logger.handlers)
