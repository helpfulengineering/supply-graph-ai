"""Password hashing for member sign-in (#570).

Argon2id at the OWASP minimum: 19 MiB, 2 iterations, parallelism 1. The
parameters live in the hash, so raising them later rehashes a password the
next time it is presented correctly.
"""

from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19 * 1024,
    parallelism=1,
    type=Type.ID,
)

# Verified when the username is unknown, so that path costs an Argon2 check
# too. Computed once: the first login of a missing account must not be the
# only one that pays for building the dummy.
DUMMY_PASSWORD_HASH = _HASHER.hash("ohm-login-dummy")

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256


def hash_password(password: str) -> str:
    return _HASHER.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _HASHER.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    return _HASHER.check_needs_rehash(hashed)


def password_problem(password: str, username: str, display_name: str) -> str | None:
    """Why this password is refused, or None when it is acceptable.

    Length only. Composition rules are not used: they push people onto
    patterns that are easier to guess. A password that is the username or
    the display name is refused because those are already public.
    """
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        return (
            f"A password is between {MIN_PASSWORD_LENGTH} and "
            f"{MAX_PASSWORD_LENGTH} characters."
        )
    folded = password.casefold()
    if folded == username.casefold() or folded == display_name.strip().casefold():
        return "Choose a password that is not your username or display name."
    return None
