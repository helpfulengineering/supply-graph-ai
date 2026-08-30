"""Which peers may speak for someone else (#411).

Uvicorn's ``ProxyHeadersMiddleware`` rewrites ``request.client`` from
``X-Forwarded-For`` when the immediate peer is trusted, and ignores the header
entirely when it is not. Everything keyed on the client address — rate
limiting, request logs, metrics — depends on getting that trust set right.

It was ``*``, meaning *trust every peer*. Uvicorn's ``_TrustedHosts`` treats
that as "always trust" and then returns the **leftmost** ``X-Forwarded-For``
entry, which is entirely client-supplied. So the address the API believed was
whatever the caller claimed: the per-client rate limit could be evaded by
sending a random value per request, and another client's budget could be
exhausted by naming them.

``*`` was chosen for a real reason — ``X-Forwarded-Proto`` has to be trusted or
Starlette builds ``http://`` redirects behind a TLS-terminating ingress — so the
fix is not to stop trusting proxies but to name which ones.

The default trusts loopback and the private ranges. The container is reachable
only through its platform ingress, which connects from inside the environment's
private network, so this keeps the proto fix working while making a forged
header from the public internet inert: an untrusted peer's forwarded headers are
not read at all. Deployments with a different topology should set
``FORWARDED_ALLOW_IPS`` explicitly rather than widening this.
"""

from __future__ import annotations

import os

#: Loopback plus RFC1918. Not "every peer" — see the module docstring.
DEFAULT_FORWARDED_ALLOW_IPS = "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"


def forwarded_allow_ips() -> str:
    """The peers whose forwarded headers this node will believe.

    ``FORWARDED_ALLOW_IPS`` overrides the default. Setting it to ``*`` is
    supported for a deployment that genuinely fronts every request with a proxy
    it controls, but it means any peer can claim any client address.
    """
    return os.getenv("FORWARDED_ALLOW_IPS") or DEFAULT_FORWARDED_ALLOW_IPS
