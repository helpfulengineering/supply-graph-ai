#!/usr/bin/env python3
"""Print sorted HTTP method + path lines for the versioned FastAPI app (api_v1).

Used for conference demos and doc audits; same logic as the inline snippet in
docs/development/conference-demo-readiness.md.

Usage:
    uv run python scripts/dump_api_routes.py
    uv run python scripts/dump_api_routes.py --count-only
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="Print only the number of operations (no paths).",
    )
    args = parser.parse_args()

    from src.core.main import api_v1

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
