"""The container entrypoint must agree with the application about strictness.

The entrypoint picks the server (production vs auto-reloading dev server) in
shell, so it cannot import ``is_production_like``. That leaves two copies of one
rule, and a comment asking the next person to keep them aligned is not a
mechanism — this test is.

It executes the REAL decision block extracted from the real script, rather than
matching its text, so a behavioural change is caught even if the wording is
unchanged.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config.schema import RELAXED_ENVIRONMENTS, is_production_like

pytestmark = pytest.mark.unit

_ENTRYPOINT = _REPO_ROOT / "deploy" / "docker" / "docker-entrypoint.sh"

# Names to compare on: the relaxed sandboxes, real deployments, an unanticipated
# name, and the odd casing/spacing a deploy tool might hand us.
_ENVIRONMENTS = [
    "development",
    "test",
    "production",
    "staging",
    "demo",
    "preprod",
    "PRODUCTION",
    "Staging",
    "",
]


def _extract_auto_detect_block() -> str:
    """The entrypoint's `USE_GUNICORN=auto` branch, verbatim from the script."""
    lines = _ENTRYPOINT.read_text(encoding="utf-8").splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if re.search(r'USE_GUNICORN.*=.*"auto"', line)
            and line.strip().startswith("if ")
        ),
        None,
    )
    assert start is not None, "could not find the auto-detect branch in the entrypoint"

    indent = len(lines[start]) - len(lines[start].lstrip())
    for end in range(start + 1, len(lines)):
        stripped = lines[end].strip()
        if stripped == "fi" and (len(lines[end]) - len(lines[end].lstrip())) == indent:
            return "\n".join(lines[start : end + 1])
    raise AssertionError("could not find the end of the auto-detect branch")


def _shell_choice(environment: str) -> bool:
    """Run the extracted block for `environment`; True means the production server."""
    script = (
        f"ENVIRONMENT={environment!r}\n"
        "USE_GUNICORN=auto\n"
        f"{_extract_auto_detect_block()}\n"
        'printf "%s" "$USE_GUNICORN"\n'
    )
    result = subprocess.run(
        ["sh", "-c", script], capture_output=True, text=True, check=True
    )
    value = result.stdout.strip()
    assert value in {"true", "false"}, f"unexpected USE_GUNICORN={value!r}"
    return value == "true"


@pytest.mark.parametrize("environment", _ENVIRONMENTS)
def test_entrypoint_agrees_with_the_application(environment):
    """The one place the predicate cannot be shared, so it is checked instead."""
    assert _shell_choice(environment) is is_production_like(environment), (
        f"entrypoint and is_production_like() disagree for {environment!r} — "
        "the shell rule must mirror src/config/schema.py::is_production_like"
    )


@pytest.mark.parametrize("environment", sorted(RELAXED_ENVIRONMENTS))
def test_sandboxes_get_the_reloading_dev_server(environment):
    assert _shell_choice(environment) is False


def test_staging_gets_the_production_server():
    """It previously got `uvicorn --reload` — a different process model from the
    environment it exists to rehearse."""
    assert _shell_choice("staging") is True


def test_an_explicit_override_still_wins():
    """`USE_GUNICORN` set explicitly must not be overwritten by auto-detection."""
    script = (
        "ENVIRONMENT=production\n"
        "USE_GUNICORN=false\n"
        f"{_extract_auto_detect_block()}\n"
        'printf "%s" "$USE_GUNICORN"\n'
    )
    result = subprocess.run(
        ["sh", "-c", script], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "false"
