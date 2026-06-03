"""GitHub raw path quoting and software.release heuristics."""

from __future__ import annotations

from src.core.packaging.builder import _looks_like_bare_release_version
from src.core.packaging.github_raw_urls import quote_github_raw_relative_path


def test_quote_github_raw_encodes_hash_in_filename() -> None:
    assert (
        quote_github_raw_relative_path(
            "electrical/pcb/foo.pretty/#6THRU-HOLE.kicad_mod"
        )
        == "electrical/pcb/foo.pretty/%236THRU-HOLE.kicad_mod"
    )


def test_quote_github_raw_preserves_slashes_between_segments() -> None:
    assert quote_github_raw_relative_path("bom/bom.json") == "bom/bom.json"


def test_looks_like_bare_release_version() -> None:
    assert _looks_like_bare_release_version("0.1.0")
    assert _looks_like_bare_release_version("v1.2.3")
    assert _looks_like_bare_release_version("2.0.0-beta1")
    assert not _looks_like_bare_release_version("tools/gc.py")
    assert not _looks_like_bare_release_version("release/v1.0.0.zip")
    assert not _looks_like_bare_release_version("https://example.com/x")
