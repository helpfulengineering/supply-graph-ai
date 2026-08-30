"""Private key material is never written world-readable (#410).

Plaintext-at-rest is a documented peacetime decision and is not what this
covers. The *permissions* were never a decision at all — just the default from
a plain text write — which left every registered person's Ed25519 signing key
readable by any local user or process on the host. Self-service registration
multiplies how many of those accumulate, and each one is custodial.
"""

import os
import stat
from pathlib import Path

import pytest

from src.core.federation.identity import (
    SECRET_DIR_MODE,
    SECRET_FILE_MODE,
    generate_identity,
    load_or_create_identity,
    secret_dir,
    write_secret_file,
)
from src.core.models.identity import Identity, IdentityKind
from src.core.storage.identity_key_store import IdentityKeyStore


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _person(tmp_path: Path) -> Path:
    store = IdentityKeyStore(tmp_path)
    key = generate_identity("Ada")
    store.save(
        key,
        Identity(
            did=key.did,
            kind=IdentityKind.PERSON,
            display_name="Ada",
            custodial=True,
        ),
    )
    return next((tmp_path / "identities").iterdir())


def test_a_persons_key_is_not_readable_by_anyone_else(tmp_path):
    key_file = _person(tmp_path)

    assert "private_key_hex" in key_file.read_text(), "fixture stopped holding a secret"
    assert _mode(key_file) == SECRET_FILE_MODE
    assert _mode(tmp_path / "identities") == SECRET_DIR_MODE


def test_the_nodes_own_key_gets_the_same_treatment(tmp_path):
    """The rule is 'this directory holds secrets', not 'this filename is special'."""
    data_dir = tmp_path / "federation"
    load_or_create_identity(data_dir, "test-node")

    assert _mode(data_dir) == SECRET_DIR_MODE
    assert _mode(data_dir / "identity.json") == SECRET_FILE_MODE


def test_a_file_is_never_briefly_wider_than_its_final_mode(tmp_path):
    """A create-then-chmod leaves a window in which the key is readable, which
    is the whole bug. The mode has to be applied at open time."""
    target = tmp_path / "secrets" / "k.json"
    observed = []

    real_fdopen = os.fdopen

    def watching_fdopen(fd, *args, **kwargs):
        # The moment the descriptor exists, before anything is written.
        observed.append(stat.S_IMODE(os.fstat(fd).st_mode))
        return real_fdopen(fd, *args, **kwargs)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(os, "fdopen", watching_fdopen)
        write_secret_file(target, "secret")

    assert observed, "write path changed; this test no longer observes creation"
    for mode in observed:
        assert mode & 0o077 == 0, f"file existed at {oct(mode)} before being tightened"


def test_files_written_before_this_version_are_repaired(tmp_path):
    """An upgrade must not leave old installations exposed."""
    import src.core.federation.identity as identity_module

    legacy_dir = tmp_path / "identities"
    legacy_dir.mkdir(parents=True)
    legacy_dir.chmod(0o755)
    legacy = legacy_dir / "did-key-zold.json"
    legacy.write_text('{"private_key_hex": "deadbeef"}')
    legacy.chmod(0o644)

    # The repair is once-per-process, so forget that this path was seen.
    identity_module._repaired_dirs.discard(str(legacy_dir.resolve()))
    secret_dir(legacy_dir)

    assert _mode(legacy) == SECRET_FILE_MODE
    assert _mode(legacy_dir) == SECRET_DIR_MODE


@pytest.mark.parametrize("umask", [0o000, 0o022, 0o077])
def test_correct_under_an_unusual_umask(tmp_path, umask):
    """umask can only clear bits, so a permissive one must not widen the file
    and a restrictive one must not leave it unreadable by its owner."""
    previous = os.umask(umask)
    try:
        target = tmp_path / f"u{umask}" / "k.json"
        write_secret_file(target, "secret")
        assert _mode(target) == SECRET_FILE_MODE
        assert _mode(target.parent) == SECRET_DIR_MODE
    finally:
        os.umask(previous)
