#!/usr/bin/env python3
"""Print sorted HTTP method + path lines for the versioned FastAPI app (api_v1).

Useful for doc audits and comparing OpenAPI inventory to narrative docs.

``--openapi PATH`` writes the spec itself, which is what regenerates the
frontend's typed client. Doing it in-process rather than over HTTP is the point:
the old route was `npx openapi-typescript http://localhost:8001/v1/openapi.json`,
so regenerating needed a running API, so nobody regenerated, so the committed
schema drifted from the app it claims to describe.

It takes a path rather than printing, because importing the app emits a startup
log line on stdout — a spec piped from here would be a spec with a log line
glued to the front of it.

Usage:
    uv run python scripts/dump_api_routes.py
    uv run python scripts/dump_api_routes.py --count-only
    uv run python scripts/dump_api_routes.py --openapi openapi.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="Print only the number of operations (no paths).",
    )
    parser.add_argument(
        "--openapi",
        metavar="PATH",
        help="Write the OpenAPI spec as JSON to PATH, for openapi-typescript.",
    )
    args = parser.parse_args()

    from src.core.main import api_v1

    if args.openapi:
        target = Path(args.openapi)
        target.write_text(json.dumps(api_v1.openapi(), indent=2), encoding="utf-8")
        print(f"# wrote {target}", flush=True)
        return

    ops: list[str] = []
    for route in api_v1.routes:
        methods = getattr(route, "methods", None) or set()
        path = getattr(route, "path", "")
        for method in sorted(methods):
            if method in ("HEAD", "OPTIONS"):
                continue
            ops.append(f"{method} {path}")

    ops.sort()
    if args.count_only:
        print(len(ops))
    else:
        for line in ops:
            print(line)
        print(f"# total: {len(ops)}", flush=True)


if __name__ == "__main__":
    main()
