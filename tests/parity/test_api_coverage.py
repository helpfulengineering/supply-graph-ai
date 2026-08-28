"""Frontend <-> API endpoint coverage gate.

``test_parity.py`` checks that the frontend touches each API *tag*. This checks
each *path*. The difference is the whole point: ``fe_api_prefixes=("/api/supply-
tree",)`` is satisfied by one call and says nothing about the other nineteen
endpoints under that tag. That gap was 91 of the API's 158 paths, including
four routers that had never had a caller and had never failed anything.

Every path the versioned app serves is either called by frontend app code or
carries a row in ``manifest.UNCALLED_ENDPOINTS`` saying why not.

When this fails, do ONE of:
  * wire the frontend call, or
  * add a row classifying the endpoint (never / planned / ui_indirect), or
  * DELETE the row, if the UI now calls what the row said it did not.

Run directly with:  uv run pytest tests/parity/test_api_coverage.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity.inventory import (
    fe_api_call_sites,
    openapi_paths,
    schema_d_ts_paths,
)
from tests.parity.manifest import (
    ENDPOINT_REASONS,
    ENDPOINT_STATUSES,
    UNCALLED_ENDPOINTS,
    uncalled_endpoint_paths,
)

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]

# The scan finds this many call sites today. The floor exists because every
# assertion below passes for free if the scanner silently stops finding
# anything — a tightened regex would turn this file green while proving
# nothing. Same guard, same reasoning as frontend/src/lib/demo/routes.test.ts.
_CALL_SITE_FLOOR = 50


def test_scan_finds_the_frontend_api_surface():
    """The scanner must actually find calls, or every other test is vacuous."""
    sites = fe_api_call_sites()
    assert len(sites) > _CALL_SITE_FLOOR, (
        f"The frontend API scan found only {len(sites)} call sites, below the "
        f"floor of {_CALL_SITE_FLOOR}. Every coverage assertion in this file "
        f"passes trivially when the scan finds nothing, so this is a broken "
        f"scanner rather than a shrunken frontend.\n"
        f"    -> check inventory._call_site_patterns and _SCAN_EXCLUDED."
    )


def test_every_api_path_is_called_or_recorded():
    """No endpoint may be unaccounted for. This is the ratchet."""
    unaccounted = sorted(
        openapi_paths() - set(fe_api_call_sites()) - uncalled_endpoint_paths()
    )
    assert not unaccounted, (
        "API paths served by the app that nothing calls and no row explains:\n  "
        + "\n  ".join(unaccounted)
        + "\n    -> wire the frontend call, or add a row to "
        "tests/parity/manifest.py UNCALLED_ENDPOINTS classifying each."
    )


def test_recorded_endpoints_are_not_actually_called():
    """A row cannot rot: the frontend calling it must fail this gate.

    For a `planned` row the deletion is the point — the backlog entry is done,
    and leaving it behind is how a ledger silently stops describing reality.
    For a `never` row it is louder: either the call is a mistake or the
    decision changed, and both need a human.
    """
    sites = fe_api_call_sites()
    rotted = [
        f"{e.path} ({e.status}) <- {sites[e.path]}"
        for e in UNCALLED_ENDPOINTS
        if e.status != "ui_indirect" and e.path in sites
    ]
    assert not rotted, (
        "Endpoints recorded as uncalled that the frontend now calls:\n  "
        + "\n  ".join(rotted)
        + "\n    -> delete the row. For 'planned' the UI shipped; for 'never' "
        "either the call is wrong or the decision was."
    )


def test_recorded_endpoints_still_exist():
    """A rename or deletion must not leave a row pointing at nothing."""
    stale = sorted(uncalled_endpoint_paths() - openapi_paths())
    assert not stale, (
        "Rows in UNCALLED_ENDPOINTS for paths the API no longer serves:\n  "
        + "\n  ".join(stale)
        + "\n    -> a rename or deletion broke the contract; fix the row."
    )


def test_endpoint_rows_are_coherent():
    """The table's own shape, checked the way AREAS' slots are."""
    problems: list[str] = []

    seen: set[str] = set()
    for endpoint in UNCALLED_ENDPOINTS:
        if endpoint.path in seen:
            problems.append(f"{endpoint.path}: declared more than once")
        seen.add(endpoint.path)

        if endpoint.status not in ENDPOINT_STATUSES:
            problems.append(f"{endpoint.path}: unknown status {endpoint.status!r}")
        if endpoint.reason not in ENDPOINT_REASONS:
            problems.append(f"{endpoint.path}: unknown reason {endpoint.reason!r}")
        if not endpoint.note.strip():
            problems.append(f"{endpoint.path}: no note — the reason IS the row")

        indirect = endpoint.status == "ui_indirect"
        has_evidence = bool(endpoint.evidence and endpoint.anchor)
        if indirect and not has_evidence:
            problems.append(
                f"{endpoint.path}: ui_indirect needs evidence and anchor, or it "
                f"is an unfalsifiable claim"
            )
        if not indirect and has_evidence:
            problems.append(
                f"{endpoint.path}: evidence/anchor belong only to ui_indirect"
            )

    assert not problems, "Malformed UNCALLED_ENDPOINTS rows:\n  " + "\n  ".join(
        problems
    )


def test_ui_indirect_evidence_still_exists():
    """The escape hatch cannot become a blanket exemption.

    A `ui_indirect` row claims the UI calls the endpoint by a URL the scanner
    cannot see. That claim is only worth anything while the call site it names
    is still there, so the file must exist and must still contain the anchor.
    """
    problems: list[str] = []
    for endpoint in UNCALLED_ENDPOINTS:
        if endpoint.status != "ui_indirect":
            continue
        source, _, _line = (endpoint.evidence or "").rpartition(":")
        path = _REPO_ROOT / source
        if not path.is_file():
            problems.append(f"{endpoint.path}: evidence file {source} does not exist")
        elif endpoint.anchor not in path.read_text(encoding="utf-8", errors="ignore"):
            problems.append(
                f"{endpoint.path}: {source} no longer contains {endpoint.anchor!r}"
            )
    assert not problems, (
        "ui_indirect rows whose evidence is gone:\n  "
        + "\n  ".join(problems)
        + "\n    -> the composed call moved or was deleted; re-point the row, "
        "or delete it if the UI no longer calls the endpoint."
    )


def test_generated_schema_matches_the_live_app():
    """The committed types must describe the API this build serves.

    Not cosmetic. The typed client is generated from that file, so a path
    missing there is a path the UI cannot call without dropping to a raw
    fetch — which is how two endpoints ended up outside the typed client with
    a comment saying so. Stale types push callers off the typed path.
    """
    drift = sorted(schema_d_ts_paths() ^ openapi_paths())
    assert not drift, (
        "frontend/src/api/generated/schema.d.ts disagrees with the live app on:\n  "
        + "\n  ".join(drift)
        + "\n    -> cd frontend && npm run gen:api"
    )
