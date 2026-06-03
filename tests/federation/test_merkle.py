"""Unit tests for federation Merkle root computation."""

from __future__ import annotations

import pytest

from src.core.federation.merkle import merkle_root


@pytest.mark.unit
def test_merkle_root_empty() -> None:
    root = merkle_root([])
    assert len(root) == 64
    assert root == merkle_root([])


@pytest.mark.unit
def test_merkle_root_single_leaf() -> None:
    leaf = "sha256:abc"
    assert merkle_root([leaf]) == leaf


@pytest.mark.unit
def test_merkle_root_is_order_independent() -> None:
    leaves = ["sha256:aaa", "sha256:bbb", "sha256:ccc"]
    assert merkle_root(leaves) == merkle_root(list(reversed(leaves)))


@pytest.mark.unit
def test_merkle_root_pairs_two_leaves() -> None:
    a, b = "sha256:111", "sha256:222"
    root = merkle_root([a, b])
    assert root != a
    assert root != b
    assert len(root) == 64
