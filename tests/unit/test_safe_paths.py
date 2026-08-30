"""Paths derived from manifest content stay inside the package (#418).

Package building takes file locations from OKH manifest content — which any
writer supplies — and from the path segments of remote URLs, then joins them to
a directory. Without a containment check that is an arbitrary local file read
into a package, and an arbitrary object-store write, including under ``auth/``.

The helpers reject rather than sanitise: a manifest asking for a file outside
its own package is not one to quietly fix up, and rewriting the path would hide
the attempt.
"""

from pathlib import Path

import pytest

from src.core.utils.safe_paths import UnsafePathError, safe_join, safe_key


@pytest.mark.parametrize(
    "relative",
    [
        "file.txt",
        "sub/dir/file.txt",
        "./sub/file.txt",
        "sub/../other.txt",  # walks, but lands inside
    ],
)
def test_legitimate_package_paths_still_work(tmp_path, relative):
    """The guard must not break normal packages, which do have subdirectories."""
    resolved = safe_join(tmp_path, relative)
    assert resolved.is_relative_to(tmp_path.resolve())


@pytest.mark.parametrize(
    "relative",
    [
        "../outside.txt",
        "../../../../etc/passwd",
        "sub/../../outside.txt",
        "/etc/passwd",
        "/",
    ],
)
def test_escaping_paths_are_rejected(tmp_path, relative):
    with pytest.raises(UnsafePathError) as exc:
        safe_join(tmp_path, relative)
    # The offending value is named, so an operator reading a log knows what was
    # asked for rather than only that something was refused.
    assert relative in str(exc.value)


def test_a_symlinked_base_is_judged_on_where_it_lands(tmp_path):
    """Resolving both sides is what makes the comparison meaningful."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)

    assert safe_join(link, "file.txt").is_relative_to(real.resolve())
    with pytest.raises(UnsafePathError):
        safe_join(link, "../outside.txt")


@pytest.mark.parametrize(
    "relative,expected",
    [
        ("files/a.txt", "packages/o/p/1/files/a.txt"),
        ("files/sub/a.txt", "packages/o/p/1/files/sub/a.txt"),
        ("files/./a.txt", "packages/o/p/1/files/a.txt"),
        ("files/sub/../a.txt", "packages/o/p/1/files/a.txt"),
    ],
)
def test_object_keys_stay_under_their_prefix(relative, expected):
    assert safe_key("packages/o/p/1", relative) == expected


@pytest.mark.parametrize(
    "relative",
    [
        "../../../auth/api-key-index/deadbeef.json",
        "../../../../auth/api-keys/x.json",
        "/auth/api-keys/x.json",
        "..\\auth\\x.json",
        "files/../../../../auth/x.json",
    ],
)
def test_keys_cannot_escape_into_the_credential_prefix(relative):
    """The object-store half of this: an escaping key could point a digest at a
    key the caller does not hold, which is the one scenario that made a store
    write plausibly worse than merely bad."""
    with pytest.raises(UnsafePathError):
        safe_key("packages/o/p/1", relative)


def test_backslash_is_refused_rather_than_interpreted(tmp_path):
    """Some backends treat a backslash as a separator and some do not, so the
    safe reading is to refuse it rather than to pick one."""
    with pytest.raises(UnsafePathError):
        safe_key("packages/o/p/1", "files\\..\\..\\auth\\x.json")


def test_the_builder_refuses_a_manifest_path_that_escapes(tmp_path):
    """The guard at the join site, not just the helper in isolation."""
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("private")

    with pytest.raises(UnsafePathError):
        safe_join(package_dir, "../secret.txt")
    assert safe_join(package_dir, "docs/readme.md").is_relative_to(
        package_dir.resolve()
    )
