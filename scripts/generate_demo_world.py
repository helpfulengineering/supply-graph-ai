#!/usr/bin/env python3
"""Emit the frontend's demo world from the canonical seed dataset.

There are two ways to get a demo world in OHM: an operator seeds records with
seed_demo_data.py, or a visitor flips the client-side Demo data toggle. They
must show the SAME world — a visitor comparing a hosted demo to their own
seeded instance should not find two different catalogs — so the client world is
generated from the seed script rather than hand-written beside it.

Regenerate after changing DESIGNS or FACILITIES:

    uv run python scripts/generate_demo_world.py

--check exits non-zero when the committed output has drifted, which is how the
gate keeps the two from separating quietly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from seed_demo_data import (  # noqa: E402
    DESIGNS,
    FACILITIES,
    build_okh,
    build_okw,
    coverage,
)

OUT = _ROOT / "frontend" / "src" / "lib" / "demo" / "world.ts"

HEADER = """/**
 * The demo world — GENERATED. Do not edit.
 *
 * Emitted from scripts/seed_demo_data.py by scripts/generate_demo_world.py, so
 * the client-side Demo data toggle shows exactly what `make seed-demo` puts in
 * an instance. Two ways to reach a demo, one world: a visitor comparing a
 * hosted demo against their own seeded instance must not find two different
 * catalogs.
 *
 * Regenerate:  uv run python scripts/generate_demo_world.py
 */

"""


def render() -> str:
    designs = [build_okh(d) for d in DESIGNS]
    facilities = [build_okw(f) for f in FACILITIES]

    spaces = [
        {
            "id": f["id"],
            "name": f["name"],
            "lat": f["location"]["coordinates"]["lat"],
            "lon": f["location"]["coordinates"]["lon"],
            "city": f["location"]["city"],
            "region": f["location"].get("region"),
            "country": f["location"]["country"],
            "source": "local",
        }
        for f in facilities
    ]

    def block(name: str, value: object) -> str:
        return f"export const {name} = {json.dumps(value, indent=2, ensure_ascii=False)} as const;\n\n"

    body = HEADER
    body += block(
        "demoOkhList",
        {
            "status": "success",
            "message": "ok",
            "pagination": {
                "page": 1,
                "page_size": 100,
                "total_items": len(designs),
                "total_pages": 1,
                "has_next": False,
                "has_previous": False,
            },
            "items": designs,
        },
    )
    body += block(
        "demoOkwSearch",
        {"results": facilities, "total": len(facilities), "page": 1, "page_size": 100},
    )
    body += block(
        "demoNetworkSpaces",
        {
            "spaces": spaces,
            "total": len(spaces),
            "local_count": len(spaces),
            "mom_count": 0,
            "mom_available": False,
        },
    )
    body += block("demoOkhDetail", {d["id"]: d for d in designs})
    body += block("demoOkwDetail", {f["id"]: f for f in facilities})
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed file has drifted"
    )
    args = parser.parse_args()

    rendered = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != rendered:
            print(
                f"DRIFT: {OUT.relative_to(_ROOT)} is stale — run scripts/generate_demo_world.py"
            )
            return 1
        print(f"OK: {OUT.relative_to(_ROOT)} matches the seed dataset")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered, encoding="utf-8")
    buildable = sum(1 for _, b in coverage() if b)
    print(
        f"wrote {OUT.relative_to(_ROOT)}: {len(DESIGNS)} designs "
        f"({buildable} buildable), {len(FACILITIES)} facilities"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
