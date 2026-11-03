"""Who may register on this node (#568).

Unset follows the security mode: peacetime and crisis are open, shielded is
closed. A value an operator stores overrides the mode.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from fastapi import HTTPException, status

from src.config import settings
from src.config.security_policy import SecurityPolicy


class Registration(str, Enum):
    OPEN = "open"
    INVITE = "invite"
    CLOSED = "closed"


def _path() -> Path:
    return Path(settings.OHM_FEDERATION_DATA_DIR).expanduser() / "registration.json"


def load() -> Registration | None:
    file = _path()
    if not file.is_file():
        return None
    return Registration(json.loads(file.read_text(encoding="utf-8"))["registration"])


def save(value: Registration) -> None:
    file = _path()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(
        json.dumps({"registration": value.value}),
        encoding="utf-8",
    )


def effective(policy: SecurityPolicy) -> Registration:
    """The value in force: an operator's choice, or the mode's default."""
    stored = load()
    if stored is not None:
        return stored
    if policy.open_registration:
        return Registration.OPEN
    return Registration.CLOSED


def refuse_uninvited(policy: SecurityPolicy) -> None:
    """Refuse signup when this node is not taking uninvited registrations."""
    stored = load()
    if stored is None:
        if policy.open_registration:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Self-service registration is disabled in "
                f"{policy.mode.value} mode; ask an operator to mint an account"
            ),
        )
    if stored is Registration.OPEN:
        return
    if stored is Registration.CLOSED:
        detail = (
            "This node is not accepting registrations. "
            "Ask an operator to create an account."
        )
    else:
        detail = "This node only accepts a registration that carries an invite."
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
