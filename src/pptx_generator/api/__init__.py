"""API factories (Flask only)."""

from .flask_app import create_app as create_flask_app

create_app = create_flask_app

__all__ = ["create_app", "create_flask_app"]
