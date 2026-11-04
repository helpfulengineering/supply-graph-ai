"""Publish a curated list: the current membership, signed by its publisher."""

from __future__ import annotations

from uuid import uuid4

from ..models.visibility import is_shareable
from .catalog import manifest_content_hash
from .identity import NodeIdentity
from .models import CuratedList, CuratedListWrite
from .store import FederationStore


class ListNotShareable(Exception):
    """A pin names a design this node will not show to a peer."""

    def __init__(self, content_hash: str) -> None:
        self.content_hash = content_hash
        super().__init__(content_hash)


class ListNotFound(Exception):
    def __init__(self, list_id: str) -> None:
        self.list_id = list_id
        super().__init__(list_id)


class SupersedesUnknown(Exception):
    """``supersedes`` must name a pin this edit removes."""

    def __init__(self, content_hash: str) -> None:
        self.content_hash = content_hash
        super().__init__(content_hash)


async def shareable_content_hashes(okh) -> set[str]:
    """Content hashes of designs a peer is allowed to fetch.

    ``viewer=None`` is the unscoped read. Publishing has to see a private
    design in order to refuse it; a request handler must not call this.
    """
    manifests, _total = await okh.list(page=1, page_size=10_000, viewer=None)
    hashes: set[str] = set()
    for manifest in manifests:
        if not is_shareable(await okh.get_visibility(manifest.id)):
            continue
        hashes.add(manifest_content_hash(manifest.to_dict()))
    return hashes


def sign_curated_list(identity: NodeIdentity, document: CuratedList) -> CuratedList:
    ordered = document.model_copy(
        update={
            "entries": sorted(document.entries, key=lambda entry: entry.content_hash)
        }
    )
    return ordered.model_copy(
        update={"signature": identity.sign_json(ordered.record_payload()).hex()}
    )


async def _refuse_hidden(okh, entries) -> None:
    shareable = await shareable_content_hashes(okh)
    for entry in entries:
        if entry.content_hash not in shareable:
            raise ListNotShareable(entry.content_hash)


async def publish_curated_list(
    identity: NodeIdentity,
    store: FederationStore,
    okh,
    body: CuratedListWrite,
) -> CuratedList:
    """Sign the current membership and store it. Sequence starts at 1."""
    await _refuse_hidden(okh, body.entries)
    document = CuratedList(
        list_id=str(uuid4()),
        name=body.name,
        publisher_did=identity.did,
        sequence=1,
        entries=body.entries,
    )
    signed = sign_curated_list(identity, document)
    store.save_list(signed)
    return signed


async def replace_curated_list(
    identity: NodeIdentity,
    store: FederationStore,
    okh,
    list_id: str,
    body: CuratedListWrite,
) -> CuratedList:
    """Publish the next membership. Sequence increases by one."""
    current = store.get_list(list_id)
    if current is None:
        raise ListNotFound(list_id)
    if identity.did != current.publisher_did:
        raise PermissionError(current.publisher_did)
    await _refuse_hidden(okh, body.entries)
    previous = {entry.content_hash for entry in current.entries}
    new_hashes = {entry.content_hash for entry in body.entries}
    for entry in body.entries:
        if entry.supersedes and (
            entry.supersedes not in previous or entry.supersedes in new_hashes
        ):
            raise SupersedesUnknown(entry.supersedes)
    document = CuratedList(
        list_id=current.list_id,
        name=body.name,
        publisher_did=current.publisher_did,
        sequence=current.sequence + 1,
        entries=body.entries,
    )
    signed = sign_curated_list(identity, document)
    store.save_list(signed)
    return signed
