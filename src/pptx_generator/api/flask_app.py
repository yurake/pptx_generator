from __future__ import annotations

import os

from flask import Flask

from pptx_generator.api.logging_config import configure_api_logging
from pptx_generator.api.routes import api_blueprint
from pptx_generator.runtime.job_queue import get_queue


def create_app() -> Flask:
    """Create Flask application for stage1-4 API."""
    app = Flask(__name__)

    logger = configure_api_logging(os.environ.get("LOG_LEVEL", "INFO"))
    app.config["API_LOGGER"] = logger
    app.config["HMAC_KEYS"] = _load_hmac_keys()
    app.config["HMAC_SKEW_SEC"] = int(os.environ.get("PPTX_API_HMAC_CLOCK_SKEW_SEC", "300"))
    app.config["BEARER_TOKEN"] = os.environ.get("PPTX_API_BEARER_TOKEN")
    app.config["WORKER_COUNT"] = int(os.environ.get("PPTX_API_WORKERS", "1"))
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("PPTX_API_MAX_BODY", str(500 * 1024 * 1024))
    )

    app.queue = get_queue()  # type: ignore[attr-defined]
    app.queue.ensure_workers(app.config["WORKER_COUNT"])

    app.register_blueprint(api_blueprint)
    return app


def _load_hmac_keys() -> list[str]:
    keys: list[str] = []
    current = os.environ.get("PPTX_API_HMAC_KEY_CURRENT")
    if current:
        keys.append(current)
    next_key = os.environ.get("PPTX_API_HMAC_KEY_NEXT")
    if next_key:
        keys.append(next_key)
    return keys
