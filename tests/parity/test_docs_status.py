"""Public documentation <-> code status gate.

The site at openhardwaremanager.org states what works today. This gate stops
those statements from drifting away from the code, the way a hand-maintained
roadmap does.

Coupling is decided by DIRECTORY, not by a frontmatter flag, because a flag like
``area: none`` is forgettable and a forgotten exemption fails open:

    docs-site/docs/about/       narrative. Parity-exempt. Requires ``reviewed:``.
    docs-site/docs/guides/      feature docs. Requires ``area:`` + ``surface:``.
    docs-site/docs/reference/   glossary, standards, generated pages.

Enforced in both directions: you cannot park a feature page in ``about/`` to
dodge the gate, and you cannot forget the exemption, because the directory IS
the exemption.

The rule that earns the mechanism is R6 — a page may not claim a capability is
available on the web app when the frontend has no route for it. That is the
exact class of error this project has already made: an API endpoint shipped
(``POST /api/okh/generate-from-url``) with no frontend call, which a docs page
would happily have described as available.

Nothing here imports MkDocs. The gate is pure Python over markdown frontmatter,
so it survives a change of site generator.

Run directly with:  uv run pytest tests/parity/test_docs_status.py -q
"""

from __future__ import annotations

import datetime as dt
import warnings
from pathlib import Path
from typing import Optional

import pytest
import yaml

from tests.parity.manifest import (
    AREAS,
    DOC_STATUSES,
    DOC_SURFACES,
    SITE_DOCS,
    doc_areas,
    site_doc_for_path,
)

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DOCS_DIR = _REPO_ROOT / "docs-site" / "docs"

# How long a narrative page may go unreviewed before R8 nags. Warning only,
# never a failure: a calendar-driven hard gate eventually fires at the worst
# moment on a page that is fine, and that is how gates get disabled.
STALE_AFTER_DAYS = 180


# --- helpers -------------------------------------------------------------


def _frontmatter(path: Path) -> dict:
    """Parse a page's YAML frontmatter. Returns {} when there is none."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    _, _, rest = text.partition("---")
    raw, sep, _ = rest.partition("\n---")
    if not sep:
        return {}
    parsed = yaml.safe_load(raw)
    return parsed if isinstance(parsed, dict) else {}


def _pages(subdir: Optional[str] = None) -> list[Path]:
    """Markdown pages under docs-site/docs, optionally scoped to a subdir."""
    root = SITE_DOCS_DIR / subdir if subdir else SITE_DOCS_DIR
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.md"))


def _rel(path: Path) -> str:
    """Page path relative to docs-site/docs, in posix form."""
    return path.relative_to(SITE_DOCS_DIR).as_posix()


def _area_by_name(name: str):
    for area in AREAS:
        if area.name == name:
            return area
    return None


# --- R1: the manifest's own rows are coherent ----------------------------


def test_r1_site_docs_declare_valid_status_and_area():
    bad_status = [d for d in SITE_DOCS if d.status not in DOC_STATUSES]
    assert not bad_status, (
        "SITE_DOCS rows with an unknown status: "
        f"{[(d.area, d.label, d.status) for d in bad_status]}\n"
        f"    -> use one of {sorted(DOC_STATUSES)}."
    )

    known = doc_areas()
    bad_area = [d for d in SITE_DOCS if d.area not in known]
    assert not bad_area, (
        "SITE_DOCS rows naming an area that does not exist: "
        f"{[(d.area, d.label) for d in bad_area]}\n"
        "    -> add an Area row, or add the name to DOC_ONLY_AREAS."
    )


def test_r1_site_docs_have_no_duplicate_pages():
    paths = [d.path for d in SITE_DOCS if d.path is not None]
    dupes = sorted({p for p in paths if paths.count(p) > 1})
    assert not dupes, f"Two SITE_DOCS rows claim the same page: {dupes}"


# --- R2/R3: directory determines the contract ----------------------------


def test_r2_guides_pages_declare_area_and_surface():
    known = doc_areas()
    problems: list[str] = []
    for page in _pages("guides"):
        meta = _frontmatter(page)
        rel = _rel(page)
        area = meta.get("area")
        surface = meta.get("surface")
        if not area:
            problems.append(f"{rel}: missing `area:`")
        elif area not in known:
            problems.append(f"{rel}: unknown area {area!r}")
        if not surface:
            problems.append(f"{rel}: missing `surface:`")
        elif surface not in DOC_SURFACES:
            problems.append(
                f"{rel}: unknown surface {surface!r} (use one of {sorted(DOC_SURFACES)})"
            )
    assert not problems, "guides/ pages must declare area + surface:\n  " + "\n  ".join(
        problems
    )


def test_r3_non_guides_pages_do_not_declare_an_area():
    """Narrative and reference pages are parity-exempt, structurally.

    Enforced in the other direction too: declaring an `area:` outside guides/ is
    how a feature page would sneak past the gate.
    """
    problems = [
        _rel(page)
        for page in _pages()
        if not _rel(page).startswith("guides/") and _frontmatter(page).get("area")
    ]
    assert not problems, (
        "Pages outside guides/ must not declare an `area:`: "
        + ", ".join(problems)
        + "\n"
        "    -> a page describing a feature belongs in guides/."
    )


# --- R4/R5: manifest and disk agree, both ways ---------------------------


def test_r4_declared_pages_exist():
    missing = [
        d.path
        for d in SITE_DOCS
        if d.path is not None and not (SITE_DOCS_DIR / d.path).is_file()
    ]
    assert not missing, (
        f"SITE_DOCS declares pages that do not exist: {missing}\n"
        "    -> write the page, or set path=None until it exists."
    )


def test_r5_guides_pages_are_declared():
    undeclared = [
        _rel(page) for page in _pages("guides") if site_doc_for_path(_rel(page)) is None
    ]
    assert not undeclared, (
        f"guides/ pages with no SITE_DOCS row: {undeclared}\n"
        "    -> add a row to tests/parity/manifest.py so the page carries a status."
    )


# --- R6: the rule that earns the mechanism -------------------------------


def test_r6_web_pages_may_not_claim_deployed_without_a_frontend_route():
    """A guide cannot say "here's how to do this in the app" with no app route.

    Scoped to `surface: web`. API, CLI, and self-host guides legitimately
    document surfaces that have no frontend route and are exempt.
    """
    problems: list[str] = []
    for page in _pages("guides"):
        meta = _frontmatter(page)
        rel = _rel(page)
        if meta.get("surface") != "web":
            continue
        doc = site_doc_for_path(rel)
        if doc is None or doc.status != "deployed":
            continue
        area = _area_by_name(doc.area)
        if area is not None and not area.fe_routes:
            problems.append(
                f"{rel}: claims 'deployed' for area {doc.area!r}, which has no "
                f"frontend route"
            )
    assert not problems, (
        "Web guides claiming a capability the frontend does not expose:\n  "
        + "\n  ".join(problems)
        + "\n    -> wire the frontend, change the status, or change the surface."
    )


# --- R9: capability-level evidence ---------------------------------------


def test_r9_deployed_capabilities_are_actually_called_by_the_frontend():
    """A capability cannot claim `deployed` if no frontend code calls its endpoint.

    R6 asks whether the *area* has any frontend route, which is too coarse: the
    `okh` area has routes (browsing designs), so R6 would pass a page claiming
    repo-URL import is available even though nothing in the frontend calls
    ``/api/okh/generate-from-url``. Status is declared per capability; this makes
    the evidence per capability too.

    ``frontend/src/api/generated/`` is excluded deliberately. That directory is
    generated from the backend's OpenAPI spec, so every endpoint appears there
    whether or not the UI has ever called it — searching it would make this
    assertion pass for everything and prove nothing.
    """
    src = _REPO_ROOT / "frontend" / "src"
    if not src.is_dir():
        pytest.skip("frontend/src not present")

    sources = [
        p
        for p in src.rglob("*.ts*")
        if "api/generated" not in p.relative_to(src).as_posix()
    ]

    problems: list[str] = []
    for doc in SITE_DOCS:
        if doc.status != "deployed" or not doc.requires_fe_call:
            continue
        needle = doc.requires_fe_call
        if not any(
            needle in p.read_text(encoding="utf-8", errors="ignore") for p in sources
        ):
            problems.append(
                f"{doc.label!r} claims 'deployed' but no frontend source calls "
                f"{needle!r}"
            )
    assert not problems, (
        "Capabilities claiming deployment the frontend does not reach:\n  "
        + "\n  ".join(problems)
        + "\n    -> wire the frontend, or change the status to in_progress/roadmap."
    )


# --- R7/R8: narrative pages decay on a schedule --------------------------


def test_r7_about_pages_declare_a_valid_review_date():
    today = dt.date.today()
    problems: list[str] = []
    for page in _pages("about"):
        meta = _frontmatter(page)
        rel = _rel(page)
        reviewed = meta.get("reviewed")
        if reviewed is None:
            problems.append(f"{rel}: missing `reviewed:`")
            continue
        if isinstance(reviewed, dt.datetime):
            reviewed = reviewed.date()
        if not isinstance(reviewed, dt.date):
            problems.append(
                f"{rel}: `reviewed:` is not a YYYY-MM-DD date ({reviewed!r})"
            )
            continue
        if reviewed > today:
            problems.append(f"{rel}: `reviewed:` is in the future ({reviewed})")
    assert not problems, "about/ pages need a valid review date:\n  " + "\n  ".join(
        problems
    )


def test_r8_stale_narrative_pages_warn_but_do_not_fail():
    """Warning only, by decision. See STALE_AFTER_DAYS."""
    today = dt.date.today()
    stale: list[str] = []
    for page in _pages("about"):
        reviewed = _frontmatter(page).get("reviewed")
        if isinstance(reviewed, dt.datetime):
            reviewed = reviewed.date()
        if not isinstance(reviewed, dt.date):
            continue  # R7 reports this
        age = (today - reviewed).days
        if age > STALE_AFTER_DAYS:
            stale.append(f"{_rel(page)} (last reviewed {age} days ago)")
    if stale:
        warnings.warn(
            "Narrative pages are due for review:\n  " + "\n  ".join(stale),
            stacklevel=1,
        )
