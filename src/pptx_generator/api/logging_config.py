import logging
import sys
from pathlib import Path

from pptx_generator.logging import (
    LOG_FORMAT,
    configure_root_logging,
    ensure_rotating_file_handler,
    ensure_stream_handler,
)


def configure_api_logging(level_name: str = "INFO") -> logging.Logger:
    """API 用のログ設定を標準出力・標準エラー・ファイルに統一する。"""

    level = getattr(logging, level_name.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    # パイプラインや下位モジュールも含めて全体にハンドラを行き渡らせる
    configure_root_logging(level=level, add_stderr=True)

    api_logger = logging.getLogger("pptx_generator.api")
    api_logger.handlers.clear()
    ensure_stream_handler(api_logger, level=level, formatter=formatter)
    ensure_stream_handler(api_logger, level=logging.ERROR, formatter=formatter, stream=sys.stderr)
    ensure_rotating_file_handler(
        api_logger,
        file_path=Path("logs") / "out.log",
        level=level,
        formatter=formatter,
    )
    api_logger.setLevel(level)
    api_logger.propagate = True

    return api_logger
