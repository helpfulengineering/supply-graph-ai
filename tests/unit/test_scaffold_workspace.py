"""The scaffold/cleanup filesystem sandbox (#512).

`ScaffoldService._write_filesystem`, `_create_and_store_zip`'s optional
`output_path`, and `CleanupService.clean`'s `project_path` all used to
resolve a caller-supplied path directly — `Path(candidate).expanduser().
resolve()` — with nothing constraining where that path could point. An
anonymous caller (until #485) or any authenticated one (after) could write
a file anywhere the API process could write (scaffold) or delete any
empty-or-stub-matching file/directory anywhere it could reach (cleanup).

`resolve_scaffold_path` is the one place both services now resolve a
caller-supplied path. It fails closed: no `SCAFFOLD_OUTPUT_ROOT` configured
means the feature is off, not "anywhere is fine" — this codebase's existing
posture for exactly this shape of default (`RELAXED_ENVIRONMENTS` in
`src/config/schema.py` is derived the same way, on purpose, "so it fails
CLOSED").
"""

from __future__ import annotations

import pytest


def _set_root(monkeypatch, root) -> None:
    monkeypatch.setenv("SCAFFOLD_OUTPUT_ROOT", str(root))


def test_refuses_when_no_root_is_configured(monkeypatch):
    monkeypatch.delenv("SCAFFOLD_OUTPUT_ROOT", raising=False)
    from src.core.services.scaffold_workspace import resolve_scaffold_path

    with pytest.raises(ValueError, match="SCAFFOLD_OUTPUT_ROOT"):
        resolve_scaffold_path("/tmp/whatever")


def test_a_path_inside_the_root_resolves(tmp_path, monkeypatch):
    _set_root(monkeypatch, tmp_path)
    from src.core.services.scaffold_workspace import resolve_scaffold_path

    target = tmp_path / "my-project"
    resolved = resolve_scaffold_path(str(target))

    assert resolved == target.resolve()


def test_a_missing_candidate_defaults_to_the_root_itself(tmp_path, monkeypatch):
    _set_root(monkeypatch, tmp_path)
    from src.core.services.scaffold_workspace import resolve_scaffold_path

    assert resolve_scaffold_path(None) == tmp_path.resolve()


def test_the_root_itself_is_accepted(tmp_path, monkeypatch):
    """The boundary case: the root is inside the root."""
    _set_root(monkeypatch, tmp_path)
    from src.core.services.scaffold_workspace import resolve_scaffold_path

    assert resolve_scaffold_path(str(tmp_path)) == tmp_path.resolve()


def test_a_sibling_directory_is_refused(tmp_path, monkeypatch):
    """The bug this exists to fix: a path that merely shares a string
    prefix with the root (`/srv/ohm-scaffolds-evil` vs `/srv/ohm-scaffolds`)
    must not pass a naive `str.startswith` check."""
    root = tmp_path / "ohm-scaffolds"
    root.mkdir()
    sibling = tmp_path / "ohm-scaffolds-evil"
    _set_root(monkeypatch, root)
    from src.core.services.scaffold_workspace import resolve_scaffold_path

    with pytest.raises(ValueError, match="scaffold workspace"):
        resolve_scaffold_path(str(sibling))


def test_traversal_out_of_the_root_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "ohm-scaffolds"
    root.mkdir()
    _set_root(monkeypatch, root)
    from src.core.services.scaffold_workspace import resolve_scaffold_path

    with pytest.raises(ValueError, match="scaffold workspace"):
        resolve_scaffold_path(str(root / ".." / "elsewhere"))


def test_an_absolute_path_elsewhere_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "ohm-scaffolds"
    root.mkdir()
    _set_root(monkeypatch, root)
    from src.core.services.scaffold_workspace import resolve_scaffold_path

    with pytest.raises(ValueError, match="scaffold workspace"):
        resolve_scaffold_path("/etc/passwd")
