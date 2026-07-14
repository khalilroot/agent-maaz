from __future__ import annotations

import os
from hashlib import sha256


def is_enabled() -> bool:
    raw = os.getenv("REQUIRE_AUTH", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def configured_token() -> str | None:
    token = os.getenv("AGENT_MAAZ_BEARER_TOKEN", "").strip()
    return token or None


def fingerprint(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()[:16]


def check(authorization_header: str | None) -> bool:
    """Validate `Authorization: Bearer <token>`. Returns True when access allowed."""
    if not is_enabled():
        return True
    expected = configured_token()
    if expected is None:
        return True
    if not authorization_header:
        return False
    if not authorization_header.lower().startswith("bearer "):
        return False
    presented = authorization_header[7:].strip()
    if not presented:
        return False
    return fingerprint(presented) == fingerprint(expected)


def error_message() -> str:
    return "missing or invalid bearer token (set AGENT_MAAZ_BEARER_TOKEN)"
