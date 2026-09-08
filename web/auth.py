# -*- coding: utf-8 -*-
"""Authentication for the narration-synth web service.

Single admin user backed by a `users` table in SQLite. Passwords are stored as
pbkdf2-hmac hashes (never plaintext). Server sessions use Starlette's
SessionMiddleware with a persistent secret generated on first start.

    POST /api/login    {username, password}            -> session cookie
    POST /api/logout
    POST /api/change-password  {old_password, new_password}
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse

import web.db as db

INITIAL_USERNAME = "admin"
INITIAL_PASSWORD = "shiping@shiping"

_PBKDF2_ITERATIONS = 120_000
_SESSION_KEY_FILE = Path(__file__).resolve().parent / ".session_secret"

SESSION_USER_KEY = "username"


# ---------------------------------------------------------------------------
# session secret
# ---------------------------------------------------------------------------
def get_session_secret() -> str:
    """Return (creating if needed) the persistent session signing secret."""
    env = os.environ.get("WEB_SESSION_SECRET")
    if env:
        return env
    if _SESSION_KEY_FILE.is_file():
        val = _SESSION_KEY_FILE.read_text(encoding="utf-8").strip()
        if val:
            return val
    val = secrets.token_hex(32)
    _SESSION_KEY_FILE.write_text(val, encoding="utf-8")
    return val


# ---------------------------------------------------------------------------
# password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return (
        f"pbkdf2${_PBKDF2_ITERATIONS}"
        f"${salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2":
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(digest, expected)


# ---------------------------------------------------------------------------
# user bootstrap + authentication
# ---------------------------------------------------------------------------
def ensure_admin_user() -> None:
    """Create the admin user on first start if no user exists."""
    if db.get_user(INITIAL_USERNAME) is None:
        db.set_password(INITIAL_USERNAME, hash_password(INITIAL_PASSWORD))


def authenticate(username: str, password: str) -> bool:
    user = db.get_user(username)
    if user is None:
        return False
    return verify_password(password, user["password_hash"])


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get(SESSION_USER_KEY))


def require_user(request: Request) -> str:
    """FastAPI dependency — returns the logged-in username or 401."""
    username = request.session.get(SESSION_USER_KEY)
    if not username:
        raise AuthError("未登录")
    return username


class AuthError(Exception):
    """Raised on authentication failures inside dependencies."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def unauthorized() -> JSONResponse:
    return JSONResponse({"detail": "未登录或会话已过期"}, status_code=401)