from __future__ import annotations

import hashlib
import hmac
import time
from typing import Iterable, Optional

from flask import g, request

from pptx_generator.api.http import error_response


def verify_auth(bearer_token: Optional[str], hmac_keys: Iterable[str], skew_sec: int) -> Optional[tuple]:
    auth_header = request.headers.get("Authorization")
    if bearer_token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        if hmac.compare_digest(token, bearer_token):
            g.auth_scheme = "bearer"
            return None
    sig = request.headers.get("X-Signature")
    ts = request.headers.get("X-Timestamp")
    if sig and ts and list(hmac_keys):
        now = int(time.time())
        try:
            ts_int = int(ts)
        except ValueError:
            return error_response(401, "unauthorized", "invalid timestamp")
        if abs(now - ts_int) > skew_sec:
            return error_response(401, "unauthorized", "timestamp skew too large")
        body_hash = hashlib.sha256(request.get_data(cache=True)).hexdigest()
        signing_str = f"{ts}\n{request.method}\n{request.path}\n{body_hash}"
        for key in hmac_keys:
            expected = hmac.new(key.encode(), signing_str.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, sig):
                g.auth_scheme = "hmac"
                return None
        return error_response(401, "unauthorized", "signature mismatch")
    return error_response(401, "unauthorized", "missing auth")
