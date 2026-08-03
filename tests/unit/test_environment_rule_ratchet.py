"""Ratchet: nothing may decide strictness by comparing the environment name.

`ENVIRONMENT` selects which per-environment config file to load. It must not
also decide how strictly the system behaves — that question has one answer,
`src.config.schema.is_production_like`, and it is derived so that an
unanticipated environment name errs toward safety.

Writing `environment == "production"` is the obvious way to add the next
production-only behaviour, and it is how the v0.10.6 incident happened: the
production worker crash-looped on missing encryption secrets while the staging
rehearsal built to catch that booted clean, because staging's name is not
"production". This test makes the obvious wrong thing fail the merge gate.

Scope is Python and Terraform, because the rule has already been duplicated
across both. Shell is deliberately excluded: the container entrypoint MUST
compare environment names — that IS the mirrored rule — so gating it would mean
allowlisting the very line the gate exists to permit. That copy is covered by
tests/unit/test_entrypoint_server_choice.py, which compares behaviour rather
than text.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories that make deployment decisions. Tests are excluded: they name
# environments legitimately, and asserting on the predicate requires saying
# "production" out loud.
_SCANNED = [
    ("src", "*.py"),
    ("deploy", "*.py"),
    ("deploy", "*.tf"),
    ("harness", "*.py"),
    ("scripts", "*.py"),
]

# Files permitted to compare the environment name directly. Every entry needs a
# reason here AND a comment at the site. Empty is the goal, and currently true:
# the derived predicate needs no literal comparison to express itself.
_ALLOWLIST: dict[str, str] = {}

# `x == "production"`, `"production" != x`, and the Terraform equivalents.
_DIRECT_COMPARISON = re.compile(
    r'(==|!=)\s*["\']production["\']|["\']production["\']\s*(==|!=)'
)


def _offenders() -> list[str]:
    found: list[str] = []
    for directory, pattern in _SCANNED:
        root = _REPO_ROOT / directory
        if not root.is_dir():
            continue
        for path in root.rglob(pattern):
            if "__pycache__" in path.parts or ".terraform" in path.parts:
                continue
            relative = path.relative_to(_REPO_ROOT).as_posix()
            if relative in _ALLOWLIST:
                continue
            for number, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if _DIRECT_COMPARISON.search(line):
                    found.append(f"{relative}:{number}: {line.strip()}")
    return found


def test_nothing_decides_strictness_by_comparing_the_environment_name():
    offenders = _offenders()

    assert not offenders, (
        "Environment name compared to 'production' directly:\n  "
        + "\n  ".join(offenders)
        + "\n\nUse src.config.schema.is_production_like() instead — the rule is "
        "derived so an unanticipated environment name is strict, not lax. "
        'In Terraform, mirror it as !contains(["development", "test"], var.environment). '
        "If a comparison is genuinely correct, add the file to _ALLOWLIST with a reason."
    )


def test_the_detector_actually_detects(tmp_path):
    """A gate that cannot fail is worse than no gate."""
    sample = tmp_path / "sample.py"
    sample.write_text('if settings.environment == "production":\n    strict()\n')

    matches = [
        line
        for line in sample.read_text().splitlines()
        if _DIRECT_COMPARISON.search(line)
    ]
    assert matches, "the detector missed a direct comparison"

    # And does not fire on legitimate uses.
    for benign in (
        'PROTECTED_ENVIRONMENTS = {"production", "prod"}',
        'contains(["test", "development", "production"], var.environment)',
        "if is_production_like(settings.environment):",
        'assert is_production_like("production") is True',
    ):
        assert not _DIRECT_COMPARISON.search(benign), benign


def test_allowlist_entries_are_justified():
    """Each exemption carries its reason, so the gate cannot rot silently."""
    for path, reason in _ALLOWLIST.items():
        assert (_REPO_ROOT / path).is_file(), f"stale allowlist entry: {path}"
        assert reason.strip(), f"allowlist entry {path} has no reason"
