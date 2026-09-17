"""The package-pull filesystem sandbox (#521).

`PackageRemoteStorage.pull_package` resolved a caller-supplied `output_dir`
directly — `Path(candidate)`, `.mkdir(parents=True, exist_ok=True)`, then
wrote remote-fetched files under it — with nothing constraining where that
path could point. Any credentialed caller (after #478 added `require_write`
to this route) could still direct an arbitrary filesystem write anywhere the
API process could reach.

Same shape, same fix as #512's scaffold sandbox: `resolve_package_pull_path`
fails closed — no `PACKAGE_PULL_OUTPUT_ROOT` configured means the feature is
off, not "anywhere is fine" — and checks `Path.is_relative_to`, not
`str.startswith`, so a sibling directory sharing a string prefix can't
escape it. Only the *caller-supplied* branch is sandboxed: an omitted
`output_dir` keeps using the server's own safe default (`packages/` in the
repo root), never caller-controlled, so it is never routed through this
check.
"""

from __future__ import annotations

import pytest


def _set_root(monkeypatch, root) -> None:
    monkeypatch.setenv("PACKAGE_PULL_OUTPUT_ROOT", str(root))


def test_refuses_when_no_root_is_configured(monkeypatch):
    monkeypatch.delenv("PACKAGE_PULL_OUTPUT_ROOT", raising=False)
    from src.core.packaging.remote_storage import resolve_package_pull_path

    with pytest.raises(PermissionError, match="PACKAGE_PULL_OUTPUT_ROOT"):
        resolve_package_pull_path("/tmp/whatever")


def test_a_path_inside_the_root_resolves(tmp_path, monkeypatch):
    _set_root(monkeypatch, tmp_path)
    from src.core.packaging.remote_storage import resolve_package_pull_path

    target = tmp_path / "pulled"
    assert resolve_package_pull_path(str(target)) == target.resolve()


def test_the_root_itself_is_accepted(tmp_path, monkeypatch):
    """The boundary case: the root is inside the root."""
    _set_root(monkeypatch, tmp_path)
    from src.core.packaging.remote_storage import resolve_package_pull_path

    assert resolve_package_pull_path(str(tmp_path)) == tmp_path.resolve()


def test_a_sibling_directory_is_refused(tmp_path, monkeypatch):
    """The bug this exists to fix: a path that merely shares a string
    prefix with the root (`/srv/ohm-packages-evil` vs `/srv/ohm-packages`)
    must not pass a naive `str.startswith` check."""
    root = tmp_path / "ohm-packages"
    root.mkdir()
    sibling = tmp_path / "ohm-packages-evil"
    _set_root(monkeypatch, root)
    from src.core.packaging.remote_storage import resolve_package_pull_path

    with pytest.raises(PermissionError, match="package-pull"):
        resolve_package_pull_path(str(sibling))


def test_traversal_out_of_the_root_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "ohm-packages"
    root.mkdir()
    _set_root(monkeypatch, root)
    from src.core.packaging.remote_storage import resolve_package_pull_path

    with pytest.raises(PermissionError, match="package-pull"):
        resolve_package_pull_path(str(root / ".." / "elsewhere"))


def test_an_absolute_path_elsewhere_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "ohm-packages"
    root.mkdir()
    _set_root(monkeypatch, root)
    from src.core.packaging.remote_storage import resolve_package_pull_path

    with pytest.raises(PermissionError, match="package-pull"):
        resolve_package_pull_path("/etc/passwd")
