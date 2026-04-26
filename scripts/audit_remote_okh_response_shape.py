#!/usr/bin/env python3
"""
Load every OKH manifest discoverable via storage and validate against OKHResponse.

Use this to find manifests that would break GET /api/okh/{id} (Pydantic) after
domain parsing — e.g. wrong element types in list fields.

Loads repo-root ``.env`` the same way as other scripts (``src.config.storage_config``).

Example::

    python scripts/audit_remote_okh_response_shape.py
    python scripts/audit_remote_okh_response_shape.py --json report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


async def _run() -> int:
    import src.config.storage_config  # noqa: F401
    from src.config.storage_config import get_default_storage_config
    from src.core.api.models.base import APIStatus
    from src.core.api.models.okh.response import OKHResponse
    from src.core.services.okh_service import OKHService
    from src.core.services.storage_service import StorageService

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write a JSON report (errors list + summary) to this path",
    )
    args = parser.parse_args()

    storage = await StorageService.get_instance()
    if not storage._configured:
        await storage.configure(get_default_storage_config())
    if not storage.manager:
        print(
            "Storage is not configured; check .env / STORAGE_PROVIDER.", file=sys.stderr
        )
        return 1

    okh = await OKHService.get_instance()
    manifests, total = await okh.list(page=1, page_size=10_000)
    print(
        f"Loaded {len(manifests)} manifest(s) from storage (total reported: {total})."
    )

    errors: List[Dict[str, Any]] = []
    for m in manifests:
        mid = str(m.id)
        title = m.title or ""
        try:
            payload = m.to_dict()
            payload.update(
                {
                    "status": APIStatus.SUCCESS,
                    "message": "audit",
                    "request_id": None,
                    "timestamp": datetime.now(),
                }
            )
            OKHResponse.model_validate(payload)
        except Exception as e:
            errors.append(
                {
                    "id": mid,
                    "title": title,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )

    print(f"OKHResponse-compatible: {len(manifests) - len(errors)}")
    print(f"Failed validation: {len(errors)}")
    for row in errors[:50]:
        print(f"  - {row['id']} | {row['title'][:60]!r} | {row['error']}")
    if len(errors) > 50:
        print(f"  ... and {len(errors) - 50} more (see --json report)")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "checked": len(manifests),
                    "failed": len(errors),
                    "errors": errors,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {args.json}")

    return 1 if errors else 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
