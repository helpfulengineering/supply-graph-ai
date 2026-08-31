"""Where credential-encryption settings are read from (#371).

The same encryption protects LLM credentials today and storage-provider
credentials next, so the ``LLM_``-prefixed names are already wrong and every
future credential type would inherit the misnomer. ``OHM_ENCRYPTION_*`` is the
name; the old one keeps working.

One resolver rather than a fallback at each read site: three call sites each
doing ``os.getenv(new) or os.getenv(old)`` is three places for the deprecation
to be forgotten when it is eventually removed.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

#: Suffix -> (preferred name, deprecated name).
_NAMES = {
    "KEY": ("OHM_ENCRYPTION_KEY", "LLM_ENCRYPTION_KEY"),
    "SALT": ("OHM_ENCRYPTION_SALT", "LLM_ENCRYPTION_SALT"),
    "PASSWORD": ("OHM_ENCRYPTION_PASSWORD", "LLM_ENCRYPTION_PASSWORD"),
}

#: Warned once per name per process. A deprecation notice on every credential
#: read would be noise an operator learns to scroll past.
_warned: set[str] = set()


def encryption_setting(suffix: str) -> Optional[str]:
    """Read one encryption setting, preferring the ``OHM_`` name.

    Returns ``None`` for unset or empty, so callers can treat both the same —
    an empty string in a deployment's environment means "not configured", not
    "configured to nothing".
    """
    preferred, deprecated = _NAMES[suffix]

    value = os.getenv(preferred)
    if value and value.strip():
        return value.strip()

    value = os.getenv(deprecated)
    if value and value.strip():
        if deprecated not in _warned:
            _warned.add(deprecated)
            logger.warning(
                "%s is deprecated; rename it to %s. The old name still works, "
                "and will keep working until a release that says otherwise — "
                "this encryption now protects more than LLM credentials.",
                deprecated,
                preferred,
            )
        return value.strip()

    return None


def encryption_names(suffix: str) -> tuple[str, str]:
    """``(preferred, deprecated)`` for a suffix, for building error messages."""
    return _NAMES[suffix]
