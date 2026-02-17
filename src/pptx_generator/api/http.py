from __future__ import annotations

from flask import jsonify


def error_response(status_code: int, code: str, message: str):
    return jsonify({"code": code, "message": message}), status_code
