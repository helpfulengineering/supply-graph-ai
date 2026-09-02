#!/usr/bin/env python3
"""Report why this node will or will not use an LLM, from inside the node.

Read-only. Run it in a deployed container when the app reports one thing and
generation does another:

    az containerapp exec -n <app> -g <rg> --command "python scripts/diagnose_llm.py"

It exists because that question could previously only be answered by pasting a
long ``python -c`` one-liner into a console, and consoles mangle quoting — an
Azure Cloud Shell ate several attempts, including a heredoc that hung. A file in
the image has no quoting to mangle.

It asks the app's own code, in the order generation asks it, and prints each
step. The two halves it exists to compare are:

  * the credential store, which is what Settings shows, and
  * ``resolve_llm_availability()``, which is what decides whether an LLM runs.

They read different state and can disagree. When they do, this says where.

Run it in **every** container that generates — the API and the Celery worker are
separate container apps with separate environments, and only the worker's answer
explains a job's behaviour.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> int:
    from src.config import settings as app_settings
    from src.config.llm_config import CredentialManager, LLMProvider
    from src.config.schema import get_settings
    from src.core.llm import availability as av
    from src.core.services.storage_config_store import load_config
    from src.core.services.storage_service import StorageService
    from src.core.storage.llm_credential_store import LLMCredentialStore
    from src.core.version import get_version

    print("== node ==")
    print(f"  version            : {get_version()}")

    settings = get_settings()
    print(f"  LLM_ENABLED        : {settings.llm_enabled}")
    print(f"  LLM_DEFAULT_PROVIDER: {settings.llm_default_provider!r}")

    print("== storage ==")
    storage = await StorageService.get_instance()
    config = load_config() or app_settings.STORAGE_CONFIG
    await storage.configure(config)
    print(f"  provider           : {config.provider}")
    print(f"  bucket             : {config.bucket_name}")
    print(f"  connected          : {storage._configured}")

    manager = CredentialManager()
    # True means credentials are encrypted with the key that ships in the source
    # tree, which the store refuses to write under.
    print(f"  default encryption : {manager.uses_default_encryption}")

    print("== credential store (what Settings shows) ==")
    store = LLMCredentialStore(storage, manager)
    try:
        rows = await store.list_status()
    except Exception as exc:  # noqa: BLE001 — report, never raise
        print(f"  UNREADABLE: {type(exc).__name__}: {exc}")
        rows = []
    if not rows:
        print("  (no stored credentials)")
    for row in rows:
        state = "readable" if row.get("readable") else "UNREADABLE — re-save it"
        active = " [active]" if row.get("is_active") else ""
        print(f"  {row['provider']:<14}{active:<9} {row.get('masked_key')}  {state}")

    try:
        recorded = await store.get_active()
        print(f"  recorded active    : {recorded.value if recorded else 'none'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  recorded active    : unreadable ({type(exc).__name__}: {exc})")

    print("== per-provider lookup (what generation asks) ==")
    for name in ("anthropic", "openai", "azure_openai"):
        try:
            key = await store.load(LLMProvider(name))
            direct = f"key ({len(key)} chars)" if key else "absent"
        except Exception as exc:  # noqa: BLE001
            direct = f"{type(exc).__name__}: {exc}"
        # _stored_key is what resolution actually calls, and it swallows its
        # exception at DEBUG — which production never emits. That silence is
        # the reason this script exists.
        found = "key" if await av._stored_key(name) else "None"
        env = "set" if av._env_key(name) else "unset"
        print(f"  {name:<14} store={direct}")
        print(f"  {'':<14} _stored_key={found}  env_key={env}")

    print("== verdict ==")
    resolved = await av.resolve_llm_availability(requested=True)
    if resolved.available:
        print(f"  an LLM WILL run: {resolved.provider} (from {resolved.source})")
    else:
        print(f"  NO LLM will run. reason: {resolved.reason}")
        print("  generated designs will report this as llm_status and degrade")
        print("  to heuristic extraction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
