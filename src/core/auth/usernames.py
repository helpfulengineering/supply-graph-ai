"""Username normalisation for member sign-in (#570).

NFKC, then lower case, then 3–32 of ``[a-z0-9._-]``. Uniqueness is a storage
concern; this only decides what string is stored.
"""

from __future__ import annotations

import re
import unicodedata

_USERNAME = re.compile(r"^[a-z0-9._-]{3,32}$")


def normalize_username(raw: str) -> str:
    return unicodedata.normalize("NFKC", raw).strip().lower()


def validate_username(raw: str) -> str:
    """Return the stored form, or raise ``ValueError`` when it is not one."""
    username = normalize_username(raw)
    if not _USERNAME.fullmatch(username):
        raise ValueError(
            "A username is 3-32 characters: letters, digits, dots, "
            "underscores and hyphens."
        )
    return username
