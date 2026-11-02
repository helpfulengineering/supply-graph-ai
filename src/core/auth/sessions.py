"""Browser session cookies (#570).

The cookie holds 32 random bytes. The server stores a SHA-256 digest in the
API-key plane with ``kind == "session"``, so recovery's revoke-all ends
sessions too. A session presented as ``Authorization: Bearer`` is refused.

Over HTTPS the cookie is ``__Host-ohm_session`` (Secure, Path=/, no Domain).
Over plain HTTP it is ``ohm_session``, because the ``__Host-`` prefix requires
Secure and a local node is allowed to run without TLS outside shielded mode.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Response

SESSION_COOKIE = "ohm_session"
HOST_SESSION_COOKIE = "__Host-ohm_session"
CSRF_COOKIE = "ohm_csrf"
HOST_CSRF_COOKIE = "__Host-ohm_csrf"

IDLE_AFTER = timedelta(days=30)
ABSOLUTE_DAYS = 90
TOUCH_AFTER = timedelta(hours=1)
_MAX_AGE_SECONDS = ABSOLUTE_DAYS * 24 * 60 * 60

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def session_cookie_name(https: bool) -> str:
    return HOST_SESSION_COOKIE if https else SESSION_COOKIE


def csrf_cookie_name(https: bool) -> str:
    return HOST_CSRF_COOKIE if https else CSRF_COOKIE


def session_idle_expired(last_seen: datetime | None, now: datetime) -> bool:
    if last_seen is None:
        return False
    return now - last_seen > IDLE_AFTER


def session_should_touch(last_seen: datetime | None, now: datetime) -> bool:
    if last_seen is None:
        return True
    return now - last_seen >= TOUCH_AFTER


def apply_session_cookies(
    response: Response,
    *,
    token: str,
    csrf: str,
    https: bool,
    shielded: bool,
) -> None:
    """Set the session and the readable CSRF cookie.

    Shielded mode omits Max-Age, so the browser drops them when it closes.
    Domain is never set.
    """
    max_age = None if shielded else _MAX_AGE_SECONDS
    response.set_cookie(
        session_cookie_name(https),
        token,
        max_age=max_age,
        path="/",
        secure=https,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        csrf_cookie_name(https),
        csrf,
        max_age=max_age,
        path="/",
        secure=https,
        httponly=False,
        samesite="strict",
    )


def clear_session_cookies(response: Response) -> None:
    """Drop both names. The scheme may have changed since the cookie was set."""
    for name, secure, httponly, samesite in (
        (SESSION_COOKIE, False, True, "lax"),
        (HOST_SESSION_COOKIE, True, True, "lax"),
        (CSRF_COOKIE, False, False, "strict"),
        (HOST_CSRF_COOKIE, True, False, "strict"),
    ):
        response.delete_cookie(
            name, path="/", secure=secure, httponly=httponly, samesite=samesite
        )


def read_session_cookie(cookies: dict[str, str]) -> str | None:
    return cookies.get(HOST_SESSION_COOKIE) or cookies.get(SESSION_COOKIE)
