"""Merkle root over catalog content hashes (sorted leaves, pairwise SHA-256)."""

from __future__ import annotations

import hashlib


def _hash_pair(left: str, right: str) -> str:
    return hashlib.sha256(f"{left}{right}".encode("utf-8")).hexdigest()


def merkle_root(leaf_hashes: list[str]) -> str:
    """
    Compute a binary Merkle root from content hashes.

    Leaves are sorted for order-independence. A single leaf returns itself.
    An odd count promotes the last leaf without pairing.
    """
    if not leaf_hashes:
        return hashlib.sha256(b"").hexdigest()
    level = sorted(leaf_hashes)
    if len(level) == 1:
        return level[0]
    while len(level) > 1:
        next_level: list[str] = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                next_level.append(_hash_pair(level[i], level[i + 1]))
            else:
                next_level.append(level[i])
        level = next_level
    return level[0]
