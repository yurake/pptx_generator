import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_api_logging(level_name: str = "INFO") -> logging.Logger:
    """Set up shared logging handlers for API and pipeline loggers."""
    logger = logging.getLogger("pptx_generator.api")
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        log_path = Path("logs") / "out.log"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            logger.warning("log file handler setup failed; continuing with stdout only")

    # avoid clobbering other loggers; only set level and attach handlers if absent
    root = logging.getLogger("pptx_generator")
    root.setLevel(level)
    if not root.handlers:
        for h in logger.handlers:
            root.addHandler(h)
    root.propagate = True

    return logger
