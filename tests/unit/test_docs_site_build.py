"""Unit tests for the public docs staging step (scripts/build_docs_site.py).

The staging step is what puts build-status claims onto the public site, so its
two transformations — badge injection and the generated "what's built" page —
need to be correct independently of whether any guide pages exist yet.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_docs_site.py"


@pytest.fixture(scope="module")
def build_docs_site():
    spec = importlib.util.spec_from_file_location("build_docs_site", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- badge injection -----------------------------------------------------


def test_badge_lands_directly_under_the_h1(build_docs_site):
    page = "# Find your space\n\nSome intro text.\n"
    out = build_docs_site._inject_badge(page, "deployed")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert lines[0] == "# Find your space"
    assert lines[1] == "> **Available now**"


def test_badge_text_differs_per_status(build_docs_site):
    page = "# Import from a URL\n"
    roadmap = build_docs_site._inject_badge(page, "roadmap")
    deployed = build_docs_site._inject_badge(page, "deployed")
    assert "Not built yet" in roadmap
    assert "Available now" in deployed
    assert roadmap != deployed


def test_page_without_an_h1_still_gets_a_badge(build_docs_site):
    """Never silently drop the status claim just because a page is malformed."""
    out = build_docs_site._inject_badge("Body text with no heading.\n", "in_progress")
    assert "Being built" in out
    assert out.startswith("> ")


def test_unknown_status_leaves_the_page_untouched(build_docs_site):
    page = "# Whatever\n\nBody.\n"
    assert build_docs_site._inject_badge(page, "not_a_status") == page


def test_only_the_first_h1_is_matched(build_docs_site):
    page = "# First\n\ntext\n\n# Second\n"
    out = build_docs_site._inject_badge(page, "deployed")
    assert out.count("> **Available now**") == 1
    assert out.index("Available now") < out.index("# Second")


# --- generated "what's built" page ---------------------------------------


def test_whats_built_declares_itself_generated(build_docs_site):
    out = build_docs_site._render_whats_built()
    assert out.startswith("---")
    assert "generated: true" in out


def test_whats_built_groups_by_status(build_docs_site):
    out = build_docs_site._render_whats_built()
    assert "## Available now" in out
    assert "## Not built yet" in out
    # Available-now must come first; a reader should not meet the gaps first.
    assert out.index("## Available now") < out.index("## Not built yet")


def test_whats_built_lists_unbuilt_capabilities_without_links(build_docs_site):
    """Capabilities with no page yet still appear — that is the honesty point."""
    out = build_docs_site._render_whats_built()
    assert "- Generate requests for quotation" in out


def test_whats_built_links_are_relative_to_reference_dir(build_docs_site):
    """The page is written to reference/, so guide links need to climb one level."""
    from tests.parity.manifest import SITE_DOCS

    linked = [d for d in SITE_DOCS if d.path]
    out = build_docs_site._render_whats_built()
    for doc in linked:
        assert f"](../{doc.path})" in out
