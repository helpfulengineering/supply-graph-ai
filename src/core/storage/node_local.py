"""Where a node keeps its own state, and the rule that none of it is an object.

A node holds three kinds of thing that must never be content in its object store:

- **Identity keys** and the node's own identity, under `OHM_FEDERATION_DATA_DIR`.
  The identity model documents them as "node-local, never in the object store and
  never federated": they are plaintext private signing keys.
- **The saved storage configuration**, whose credentials are for the *next*
  backend and would be orphaned the moment the switch took effect.
- **The API liveness marker** (#544), a heartbeat file beside the saved
  configuration. It names the backend a running API is serving from — node
  state describing the node, not an object a client asked to store.

Both are read and written directly on the filesystem, never through the storage
layer. That is only safe while the storage layer cannot see them, and it can when
the object root is a parent of them: Compose mounts one volume at `/app/storage`,
uses it as the object root, and keeps the identity plane at
`/app/storage/federation`. Every full walk of the store then lists the keys, and a
`--mode migrate` to a cloud provider or a backup copies them (#530).

So the local provider derives what to protect from the node's real settings, here,
rather than from a list of reserved names. Protecting what is *actually* node-local
means a custom `OHM_FEDERATION_DATA_DIR` is covered, a layout that keeps them outside
the object root (the installer's) is left alone, and no key name on any other
provider (a cloud container that happens to hold a `federation/` prefix) is taken
away.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from ..utils.safe_paths import UnsafePathError


class NodeLocalKeyError(UnsafePathError):
    """An object key that names this node's own state, which is never an object."""


def node_local_paths() -> List[Path]:
    """Filesystem locations that hold this node's own state.

    The identity directory (a tree), the saved storage-configuration file, and
    the API liveness marker (each a single file: its directory may be shared
    with real objects, so only the file is protected). Resolved on every call
    so a changed setting is honoured.
    """
    from src.config import settings

    from ..services.storage_config_store import config_path
    from ..services.storage_liveness import marker_path

    return [
        Path(os.path.expanduser(str(settings.OHM_FEDERATION_DATA_DIR))),
        config_path(),
        marker_path(),
    ]
