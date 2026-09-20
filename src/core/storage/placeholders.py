"""The scaffold's own placeholder objects, and the one rule for recognising them.

Scaffolding (`StorageOrganizer.create_directory_structure`) writes a `.gitkeep`
object under each top-level prefix so the directory exists in blob storage,
where a prefix with nothing under it does not. It is bookkeeping, not content.

Anything that enumerates the store to count or list what a node *has* must skip
it. The rule lives here, alone, because it used to be decided per reader — the
health counter and the OKW listing counted it, the OKH listing happened to reject
it — and one placeholder was three different answers.

Recognised by key, not by the `file-type: directory_placeholder` label the
scaffold also stamps on it: a listing does not always carry metadata, and reading
it back would cost a request per object. The key is what the scaffold writes and
is the same on every provider.

Deliberately not applied to whole-store operations (backup, transfer, wipe): they
must see everything, and a placeholder that travels with its prefix is harmless.
"""

from __future__ import annotations

PLACEHOLDER_FILENAME = ".gitkeep"


def is_scaffold_placeholder(key: str) -> bool:
    """True for an object key that is a scaffold placeholder, at any depth."""
    return key.rsplit("/", 1)[-1] == PLACEHOLDER_FILENAME
