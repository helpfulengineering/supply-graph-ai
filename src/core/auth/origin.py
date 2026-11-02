"""Same-origin check for cookie-authenticated writes and for sign-in (#570).

A browser sends ``Origin`` on a cross-site POST. A missing ``Origin`` is a
non-browser client (the CLI, tests, curl) and is allowed. ``*`` in the CORS
list does not allow every origin here: a wildcard is not an entry a browser
sends.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from src.config.security_policy import SecurityMode, get_security_policy
from src.config.settings import CORS_ORIGINS


def assert_password_channel(https: bool) -> None:
    """Shielded mode refuses a password sent over plain HTTP."""
    policy = get_security_policy()
    if policy.mode == SecurityMode.SHIELDED and not https:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password sign-in requires HTTPS while this node is shielded.",
        )


def request_is_https(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto")
    if forwarded:
        return forwarded.split(",")[0].strip().lower() == "https"
    return request.url.scheme == "https"


def assert_allowed_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    )
    forwarded = request.headers.get("x-forwarded-proto")
    scheme = forwarded.split(",")[0].strip() if forwarded else request.url.scheme
    own = f"{scheme}://{host.split(',')[0].strip()}"
    if origin == own:
        return
    allowed = [item for item in CORS_ORIGINS if item and item != "*"]
    if origin in allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This request's origin is not allowed.",
    )
