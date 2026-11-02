"""Password, username and session rules for member sign-in (#570)."""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException, Response

from src.config.security_policy import SecurityMode, get_security_policy
from src.core.auth.login_limit import (
    clear_login_attempts,
    login_blocked,
    note_login_failure,
)
from src.core.auth.passwords import (
    hash_password,
    password_needs_rehash,
    password_problem,
    verify_password,
)
from src.core.auth.origin import assert_password_channel
from src.core.auth.sessions import (
    HOST_SESSION_COOKIE,
    SESSION_COOKIE,
    apply_session_cookies,
    session_cookie_name,
    session_idle_expired,
    session_should_touch,
)
from src.core.auth.usernames import normalize_username, validate_username
from src.core.models.account import Account


def test_a_password_hash_is_argon2id_and_verifies():
    hashed = hash_password("correct horse")
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong horse", hashed)
    assert not password_needs_rehash(hashed)


def test_a_short_password_is_refused_and_a_long_one_is_not():
    assert password_problem("short", "ada", "Ada")
    assert password_problem("x" * 257, "ada", "Ada")
    assert password_problem("correct horse", "ada", "Ada") is None


def test_a_password_that_is_the_username_or_display_name_is_refused():
    assert password_problem("ada-lovelace", "Ada-Lovelace", "Someone")
    assert password_problem("Ada Lovelace", "ada", "ada lovelace")


def test_usernames_are_folded_and_constrained():
    assert validate_username("  Ada.Lovelace ") == "ada.lovelace"
    assert normalize_username("Ada") == "ada"
    with pytest.raises(ValueError):
        validate_username("ab")
    with pytest.raises(ValueError):
        validate_username("has space")
    with pytest.raises(ValueError):
        validate_username("a" * 33)


def test_the_session_cookie_name_follows_the_scheme():
    assert session_cookie_name(False) == SESSION_COOKIE
    assert session_cookie_name(True) == HOST_SESSION_COOKIE


def test_a_session_goes_idle_after_thirty_days_and_is_touched_hourly():
    now = datetime(2026, 6, 1, 12, 0, 0)
    assert not session_idle_expired(now - timedelta(days=30), now)
    assert session_idle_expired(now - timedelta(days=30, seconds=1), now)
    assert not session_idle_expired(None, now)
    assert session_should_touch(now - timedelta(hours=1), now)
    assert not session_should_touch(now - timedelta(minutes=59), now)


def test_login_slows_after_five_failures_and_recovers_after_a_quiet_window():
    clear_login_attempts()
    for i in range(5):
        assert not login_blocked("ada", now=float(i))
        note_login_failure("ada", now=float(i))
    assert login_blocked("ada", now=5)
    assert not login_blocked("ada", now=5 + 60)
    assert not login_blocked("ada", now=5 + 15 * 60)
    clear_login_attempts()


def test_shielded_mode_refuses_a_password_over_plain_http(monkeypatch):
    monkeypatch.setattr(
        "src.core.auth.origin.get_security_policy",
        lambda: get_security_policy(SecurityMode.SHIELDED),
    )
    with pytest.raises(HTTPException) as exc:
        assert_password_channel(False)
    assert exc.value.status_code == 403
    assert_password_channel(True)


def test_a_shielded_session_cookie_expires_with_the_browser():
    response = Response()
    apply_session_cookies(
        response, token="session", csrf="csrf", https=True, shielded=True
    )
    cookies = response.headers.getlist("set-cookie")
    session = next(c for c in cookies if c.startswith("__Host-ohm_session="))
    assert "Max-Age" not in session
    assert "HttpOnly" in session
    assert "Secure" in session

    ordinary = Response()
    apply_session_cookies(
        ordinary, token="session", csrf="csrf", https=False, shielded=False
    )
    plain = ordinary.headers.getlist("set-cookie")
    assert any(c.startswith("ohm_session=") and "Max-Age=" in c for c in plain)
    assert all(not c.startswith("__Host-") for c in plain)


def test_an_account_response_does_not_carry_the_password_hash():
    account = Account(display_name="Ada", username="ada", password_hash="secret")
    assert account.password_hash == "secret"
    assert "password_hash" not in account.model_dump()
