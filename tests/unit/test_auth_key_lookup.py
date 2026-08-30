"""Authentication costs the same whether a node has one key or a thousand (#409).

Validation used to bcrypt-check keys until one matched, so a valid token cost
half a scan and an invalid one cost a whole scan — 186ms per key on the machine
this was measured on. Self-service registration (#403) made the key count grow
with every visitor, turning a bounded cost into a denial-of-service vector.

These assert the property rather than the implementation: what matters is the
*number of bcrypt verifications*, because that is the entire cost.
"""

import os
from unittest.mock import patch

import pytest

from src.core.models.auth import APIKeyCreate
from src.core.services.auth_service import AuthenticationService
from src.core.storage.account_storage import AccountStorage
from src.core.storage.auth_storage import AuthStorage


class _InMemoryManager:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self.listings = 0

    async def put_object(self, key, data, content_type=None, metadata=None):
        self._objects[key] = data

    async def get_object(self, key):
        return self._objects[key]

    async def delete_object(self, key):
        self._objects.pop(key, None)

    async def list_objects(self, prefix=None):
        self.listings += 1
        for key, data in list(self._objects.items()):
            if prefix is None or key.startswith(prefix):
                yield {"key": key, "data": data}


class _FakeStorageService:
    def __init__(self) -> None:
        self.manager = _InMemoryManager()


@pytest.fixture
def service() -> AuthenticationService:
    svc = AuthenticationService()
    storage = _FakeStorageService()
    svc._auth_storage = AuthStorage(storage)
    svc._account_storage = AccountStorage(storage)
    svc._initialized = True
    return svc


async def _mint(service, name: str) -> str:
    resp = await service.create_api_key(APIKeyCreate(name=name, permissions=["read"]))
    return resp.token


def _count_bcrypt():
    """Count real bcrypt calls, which are the whole cost of a request.

    Patched at bcrypt itself rather than at the service's verifier: since the
    digest replaced bcrypt on the fast path, counting verifier calls would
    count cheap comparisons and report a cost that is no longer being paid.
    """
    import bcrypt as bcrypt_module

    return patch.object(bcrypt_module, "checkpw", side_effect=bcrypt_module.checkpw)


@pytest.mark.asyncio
async def test_valid_token_costs_one_bcrypt_regardless_of_key_count(service):
    tokens = [await _mint(service, f"key-{i}") for i in range(25)]

    with _count_bcrypt() as verify:
        user = await service.validate_api_key(tokens[0])
        assert user is not None
        first = verify.call_count

    with _count_bcrypt() as verify:
        # The last key minted is the worst case for a scan: it was at the end.
        await service.validate_api_key(tokens[-1])
        last = verify.call_count

    assert first == 0, f"a modern key still cost {first} bcrypt call(s)"
    assert last == 0, f"cost depends on position in the store: {last}"


@pytest.mark.asyncio
async def test_invalid_token_costs_no_bcrypt_at_all(service):
    """The cheapest request for an attacker used to be the most expensive one
    for the node: a bogus token matched nothing, so it scanned everything."""
    for i in range(25):
        await _mint(service, f"key-{i}")

    from fastapi import HTTPException

    with _count_bcrypt() as verify:
        with pytest.raises(HTTPException) as exc:
            await service.validate_api_key("not-a-real-token")
        assert exc.value.status_code == 401
        assert verify.call_count == 0, (
            f"an unknown token triggered {verify.call_count} bcrypt "
            "verification(s); it should resolve to nothing by lookup alone"
        )


@pytest.mark.asyncio
async def test_unknown_token_does_not_list_the_key_store(service):
    """Counting bcrypt alone is not enough to call this fixed.

    The first version of this fix left unknown tokens falling through to a full
    ``list_keys()`` — no bcrypt, but one object read per key, which on a remote
    object store is the same denial-of-service shape a step quieter.
    """
    from fastapi import HTTPException

    for i in range(25):
        await _mint(service, f"key-{i}")

    manager = service._auth_storage.storage_service.manager
    # Prime the one-shot legacy check the way a live node would: a first
    # request settles it, and every request after pays nothing for it.
    with pytest.raises(HTTPException):
        await service.validate_api_key("bogus-1")

    manager.listings = 0
    with pytest.raises(HTTPException):
        await service.validate_api_key("bogus-2")
    assert manager.listings == 0, (
        f"an unknown token listed the key store {manager.listings} time(s); "
        "it should resolve to nothing by lookup alone"
    )


@pytest.mark.asyncio
async def test_a_key_issued_before_the_index_still_authenticates(service):
    """Pre-#409 keys have no digest and can never gain one — a bcrypt hash is
    not reversible — so they keep the old scan, and must keep working."""
    token = await _mint(service, "legacy")
    stored = (await service._auth_storage.list_keys())[0]
    stored.token_digest = None
    await service._auth_storage.save_key(stored)

    user = await service.validate_api_key(token)
    assert user is not None
    assert user.name == "legacy"


@pytest.mark.asyncio
async def test_the_scan_is_bounded_by_legacy_keys_not_by_all_keys(service):
    """The fix is not that scanning is gone, but that it stops growing."""
    legacy_token = await _mint(service, "legacy")
    stored = (await service._auth_storage.list_keys())[0]
    stored.token_digest = None
    await service._auth_storage.save_key(stored)

    for i in range(25):
        await _mint(service, f"modern-{i}")

    with _count_bcrypt() as verify:
        await service.validate_api_key(legacy_token)
        assert verify.call_count == 1, (
            "the legacy scan should cover only keys without a digest, not the "
            f"25 modern keys added after it (took {verify.call_count})"
        )


@pytest.mark.asyncio
async def test_revoked_and_expired_keys_are_still_refused(service):
    from datetime import datetime, timedelta

    from fastapi import HTTPException

    revoked_token = await _mint(service, "revoked")
    expired_token = await _mint(service, "expired")

    keys = {k.name: k for k in await service._auth_storage.list_keys()}
    await service.revoke_api_key(keys["revoked"].key_id)
    expired = keys["expired"]
    expired.expires_at = datetime.utcnow() - timedelta(days=1)
    await service._auth_storage.save_key(expired)

    for token in (revoked_token, expired_token):
        with pytest.raises(HTTPException) as exc:
            await service.validate_api_key(token)
        assert exc.value.status_code == 401


@pytest.mark.benchmark
@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv("OHM_BENCH"),
    reason="timing benchmark; run with OHM_BENCH=1 (mints keys, ~1 min)",
)
@pytest.mark.asyncio
async def test_benchmark_authentication_is_flat_across_key_counts(service):
    """Wall-clock evidence for the property the tests above assert by count.

    Opt-in because it mints real bcrypt hashes. The assertions above are the
    regression guard — they are deterministic and fast, where a timing
    assertion in CI is a flake waiting to happen. This exists so the claim can
    be re-measured on demand:

        OHM_BENCH=1 .venv/bin/python -m pytest \
            tests/unit/test_auth_key_lookup.py -k benchmark -s
    """
    import time

    token = await _mint(service, "subject")
    timings = {}
    minted = 1
    for target in (1, 10, 50):
        while minted < target:
            await _mint(service, f"filler-{minted}")
            minted += 1
        start = time.perf_counter()
        for _ in range(3):
            await service.validate_api_key(token)
        timings[target] = (time.perf_counter() - start) / 3

    for count, seconds in timings.items():
        print(f"  {count:>4} keys -> {seconds * 1000:7.1f} ms per authentication")

    worst = max(timings.values())
    best = min(timings.values())
    # A ratio alone is a flake at these speeds: with sub-millisecond timings,
    # scheduler noise makes 0.05ms look three times worse than 0.02ms. Scaling
    # is what is under test, so the ratio applies only once the numbers are
    # large enough to mean anything; below that an absolute ceiling is the real
    # assertion, and a scan over 50 keys could not possibly fit inside it.
    if best > 0.005:
        assert worst < best * 3, f"cost still scales with key count: {timings}"
    else:
        assert worst < 0.05, f"cost is no longer roughly constant: {timings}"


# --- The premise the digest rests on ----------------------------------------
#
# Verifying by SHA-256 instead of bcrypt is sound *because* the token has no
# brute-force surface. That is an assumption about the generator, so it is
# pinned here rather than believed: if someone shortens the token or swaps the
# source of randomness, this fails, and the reasoning above it stops being true
# in a way a reader will notice.


def test_tokens_carry_the_entropy_the_digest_argument_assumes():
    service = AuthenticationService()
    tokens = [service._generate_token() for _ in range(200)]

    assert len(set(tokens)) == len(tokens), "generator produced a collision"
    for token in tokens:
        # 32 random bytes, url-safe base64, padding stripped.
        assert len(token) == 43, f"token length changed: {len(token)} for {token!r}"
        assert all(c.isalnum() or c in "-_" for c in token), f"charset: {token!r}"


def test_the_generator_uses_a_cryptographic_source():
    """A digest is only as unreversible as its input is unpredictable."""
    import inspect

    source = inspect.getsource(AuthenticationService._generate_token)
    assert "secrets." in source, (
        "token generation no longer uses the secrets module; verifying by plain "
        "digest assumes a CSPRNG and is unsafe without one"
    )


@pytest.mark.asyncio
async def test_an_index_entry_pointing_at_another_key_does_not_authenticate(service):
    """Verification reads the digest off the *key record*, not off the lookup.

    Without that, writing an index object would be an authentication bypass —
    which is the only thing bcrypt was still defending on this path.
    """
    from fastapi import HTTPException

    victim_token = await _mint(service, "victim")
    attacker_token = await _mint(service, "attacker")

    keys = {k.name: k for k in await service._auth_storage.list_keys()}
    # Point the attacker's digest at the victim's key id.
    storage = service._auth_storage
    manager = storage.storage_service.manager
    import json

    attacker_digest = service._token_digest(attacker_token)
    await manager.put_object(
        storage._get_index_key(attacker_digest),
        json.dumps({"key_id": str(keys["victim"].key_id)}).encode("utf-8"),
    )

    with pytest.raises(HTTPException) as exc:
        await service.validate_api_key(attacker_token)
    assert exc.value.status_code == 401

    # The victim's own token still works, so the redirect broke nothing else.
    assert (await service.validate_api_key(victim_token)).name == "victim"
