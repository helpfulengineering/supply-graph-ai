"""An unauthenticated caller outside production is a person, not nobody.

With writes unenforced in development, a record created without a key was
attributed to nobody — and `private` is the create default — so it persisted to
storage and then vanished from every listing, including for whoever had just
written it. Reproduced before the fix: a manifest created anonymously landed on
disk while `GET /v1/api/okh` answered `total_items: 0`.

The fix is an identity (`DEV_LOCAL_ACCOUNT`), not a widened scope. The
difference is what these tests exist to hold:

* `test_dev_local_does_not_own_another_account_s_record` — the relaxation
  confers no sight of anyone else's records, so it cannot become a backdoor.
* `test_records_written_in_dev_are_invisible_in_production` — if development
  configuration ever reaches a real deployment, as it has in this repository
  once already, nothing is disclosed.

Without the second, a wrong `ENVIRONMENT` would be a confidentiality incident
rather than a misconfiguration.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.api.dependencies import created_by  # noqa: E402
from src.core.models.visibility import (  # noqa: E402
    ANONYMOUS_SCOPE,
    DEV_LOCAL_ACCOUNT,
    DEV_LOCAL_SCOPE,
)

pytestmark = pytest.mark.unit


def test_unauthenticated_writes_are_attributed_outside_production(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    assert created_by(None) == DEV_LOCAL_ACCOUNT


def test_unauthenticated_writes_are_attributed_to_nobody_in_production(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    assert created_by(None) is None


@pytest.mark.parametrize("environment", ["staging", "prod", "anything-unknown"])
def test_unknown_environments_are_production_like(monkeypatch, environment):
    """Only `development` and `test` relax; everything else is a deployment.

    `schema.py` carries the scar tissue: a guard once compared against the
    literal "production", so staging was laxer than production and the
    rehearsal passed while production broke.
    """
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", environment)
    assert created_by(None) is None


def test_dev_local_owns_what_it_wrote():
    assert DEV_LOCAL_SCOPE.owns(None, DEV_LOCAL_ACCOUNT) is True


def test_dev_local_does_not_own_another_account_s_record():
    """The property that stops this being a backdoor."""
    assert DEV_LOCAL_SCOPE.owns(None, "someone-else") is False
    assert DEV_LOCAL_SCOPE.owns("did:key:zSomeoneElse", None) is False
    assert DEV_LOCAL_SCOPE.owns(None, None) is False


def test_records_written_in_dev_are_invisible_in_production():
    """Development configuration reaching production must disclose nothing.

    A record attributed to `dev-local` is owned by an account that exists on no
    real deployment, so the production anonymous scope cannot see it — whatever
    the environment flag was when it was written. The second assertion is the
    calibration: this scope owns nothing at all, so the first is not passing by
    accident.
    """
    assert ANONYMOUS_SCOPE.owns(None, DEV_LOCAL_ACCOUNT) is False
    assert ANONYMOUS_SCOPE.owns(None, "anyone") is False
