#!/usr/bin/env python3
"""Seed a coherent demo dataset (OKH designs + OKW facilities) into storage.

Why this exists, given ``generate_synthetic_data.py`` already makes records:
that script produces *volume* — randomized data for load and matching
experiments. This one produces a *fixture*: a small, hand-curated,
deterministic world where the golden path actually completes. Every design is
buildable by at least one facility, so browse → match → supply tree yields
results instead of an empty state, and the facet axes the catalog UI exposes
(category, process, license) each have more than one value to filter on.

Determinism is the point. IDs are UUIDv5 derived from a fixed namespace and the
record's name, so re-running is idempotent, records keep stable URLs across
reseeds, and tests can deep-link to a known id. Nothing here is random.

Records are written straight to the local storage tree rather than through the
API, so seeding works with no server running and no API key.

Seed before starting the API, or restart it afterwards: list responses are
cached (``cache_backend``, 1h), so records written underneath a running server
do not appear until the cache turns over. Writing to storage is the whole
mechanism here — there is no invalidation hook to call.

Usage:
    uv run python scripts/seed_demo_data.py                  # seed ./storage
    uv run python scripts/seed_demo_data.py --clear          # wipe demo records first
    uv run python scripts/seed_demo_data.py --storage-dir /tmp/ohm-demo
    uv run python scripts/seed_demo_data.py --summary        # report, write nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Fixed namespace → the same name always yields the same id, on every machine.
_NAMESPACE = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")


def demo_id(kind: str, name: str) -> str:
    """Stable id for a demo record. Same input, same uuid, forever."""
    return str(uuid.uuid5(_NAMESPACE, f"ohm-demo:{kind}:{name}"))


# --------------------------------------------------------------------------
# The world.
#
# Processes are the join key between the two tables: a design matches a
# facility when the facility's processes cover the design's. The coverage is
# deliberately uneven — some designs match many facilities, one matches
# exactly one — so ranking, near-miss, and "no match" paths all have data.
# --------------------------------------------------------------------------

DESIGNS: list[dict] = [
    {
        "title": "Open Ventilator",
        "function": "Emergency pressure-controlled ventilator for field hospitals",
        "category": "Medical & Health",
        "processes": ["3d_printing", "cnc_machining"],
        "license": "CERN-OHL-S-2.0",
        "licensor": "Open Source Medical Supplies",
        "keywords": ["medical", "respiratory", "emergency"],
        "materials": ["PETG", "Aluminium 6061"],
    },
    {
        "title": "Face Shield",
        "function": "Reusable protective face shield with replaceable visor",
        "category": "Medical & Health",
        "processes": ["3d_printing", "laser_cutting"],
        "license": "GPL-2.0",
        "licensor": "Prusa Research",
        "keywords": ["medical", "ppe", "protective"],
        "materials": ["PETG", "PET sheet"],
    },
    {
        "title": "Solar Food Dryer",
        "function": (
            "Passive solar dehydrator holding a steady drying temperature "
            "to preserve fruit and vegetables"
        ),
        "category": "Cooking & Food Preparation",
        "processes": ["woodworking", "assembly"],
        "license": "CC-BY-SA-4.0",
        "licensor": "Appropedia Community",
        "keywords": ["food", "solar", "preservation"],
        "materials": ["Plywood", "Glass", "Mesh"],
    },
    {
        "title": "Grain Mill",
        "function": "Hand-cranked grain mill with replaceable burr plates",
        "category": "Cooking & Food Preparation",
        "processes": ["casting", "cnc_machining"],
        "license": "CERN-OHL-W-2.0",
        "licensor": "Open Source Ecology",
        "keywords": ["food", "milling", "manual"],
        "materials": ["Cast iron", "Steel"],
    },
    {
        "title": "Bias Tape Maker",
        "function": "Printed sewing jig that folds fabric strips into bias tape",
        "category": "Manufacturing & Hardware Production",
        "processes": ["3d_printing"],
        "license": "CC-BY-4.0",
        "licensor": "Sonia Cook-Broen",
        "keywords": ["textile", "sewing", "jig"],
        "materials": ["PLA"],
    },
    {
        "title": "Wind Turbine Blade Jig",
        "function": "Layup jig for small-scale composite wind turbine blades",
        "category": "Manufacturing & Hardware Production",
        "processes": ["cnc_machining", "composite_layup"],
        "license": "CERN-OHL-P-2.0",
        "licensor": "Wind Empowerment",
        "keywords": ["energy", "composite", "tooling"],
        "materials": ["MDF", "Epoxy"],
    },
    {
        "title": "Water Quality Sensor",
        "function": "Open telemetry probe for turbidity and dissolved solids",
        "category": "Environmental Monitoring",
        "processes": ["pcb_assembly", "3d_printing"],
        "license": "TAPR-OHL-1.0",
        "licensor": "Public Lab",
        "keywords": ["environment", "water", "sensor"],
        "materials": ["FR4", "ABS"],
    },
    {
        "title": "Microscope Stage",
        # Only Rotterdam Precision Works covers precision_grinding: this design
        # is the single-match case, and the reason that facility exists.
        "function": "Motorised XY stage for a field microscope",
        "category": "Scientific Instruments",
        "processes": ["precision_grinding", "cnc_machining"],
        "license": "CERN-OHL-S-2.0",
        "licensor": "Open Labware",
        "keywords": ["science", "optics", "precision"],
        "materials": ["Aluminium 6061", "Brass"],
    },
    {
        "title": "Peristaltic Pump",
        "function": "Laboratory peristaltic pump for metering liquid reagent flow",
        "category": "Scientific Instruments",
        "processes": ["3d_printing", "pcb_assembly"],
        "license": "CERN-OHL-W-2.0",
        "licensor": "Open Labware",
        "keywords": ["laboratory", "fluid", "pump", "dosing"],
        "materials": ["PLA", "Silicone tubing"],
    },
    {
        "title": "Soil Test Meter",
        "function": "Handheld meter for field measurement of soil moisture and pH",
        "category": "Environmental Monitoring",
        "processes": ["pcb_assembly", "laser_cutting"],
        "license": "TAPR-OHL-1.0",
        "licensor": "Public Lab",
        "keywords": ["measurement", "soil", "agriculture", "test"],
        "materials": ["FR4", "Acrylic"],
    },
]

FACILITIES: list[dict] = [
    {
        "name": "Boston Community Fab Lab",
        "city": "Boston",
        "region": "Massachusetts",
        "country": "US",
        "lat": 42.3601,
        "lon": -71.0589,
        "access_type": "Membership",
        "status": "Active",
        "processes": ["3d_printing", "laser_cutting", "cnc_machining"],
        "equipment": [
            ("3D Printer", "3d_printing", "Prusa", "MK4"),
            ("Laser Cutter", "laser_cutting", "Epilog", "Fusion Pro"),
            ("CNC Mill", "cnc_machining", "Tormach", "1100MX"),
        ],
    },
    {
        "name": "Detroit Makerspace",
        "city": "Detroit",
        "region": "Michigan",
        "country": "US",
        "lat": 42.3314,
        "lon": -83.0458,
        "access_type": "Public",
        "status": "Active",
        "processes": ["3d_printing", "woodworking", "assembly", "welding"],
        "equipment": [
            ("3D Printer", "3d_printing", "Bambu Lab", "X1C"),
            ("Table Saw", "woodworking", "SawStop", "PCS175"),
            ("MIG Welder", "welding", "Miller", "Multimatic 215"),
        ],
    },
    {
        "name": "Nairobi Innovation Hub",
        "city": "Nairobi",
        "region": "Nairobi County",
        "country": "KE",
        "lat": -1.2921,
        "lon": 36.8219,
        "access_type": "Public",
        "status": "Active",
        "processes": ["3d_printing", "woodworking", "assembly", "pcb_assembly"],
        "equipment": [
            ("3D Printer", "3d_printing", "Creality", "K1 Max"),
            ("Pick and Place", "pcb_assembly", "Neoden", "K1830"),
            ("Bandsaw", "woodworking", "Record Power", "BS350"),
        ],
    },
    {
        "name": "Rotterdam Precision Works",
        "city": "Rotterdam",
        "region": "South Holland",
        "country": "NL",
        "lat": 51.9244,
        "lon": 4.4777,
        "access_type": "Restricted",
        "status": "Active",
        "processes": ["cnc_machining", "precision_grinding", "casting"],
        "equipment": [
            ("5-Axis Mill", "cnc_machining", "DMG Mori", "DMU 50"),
            ("Surface Grinder", "precision_grinding", "Okamoto", "ACC-64DX"),
            ("Induction Furnace", "casting", "Inductotherm", "VIP-30"),
        ],
    },
    {
        "name": "São Paulo Composites Cooperative",
        "city": "São Paulo",
        "region": "São Paulo",
        "country": "BR",
        "lat": -23.5505,
        "lon": -46.6333,
        "access_type": "Membership",
        "status": "Active",
        "processes": ["composite_layup", "cnc_machining", "assembly"],
        "equipment": [
            ("Autoclave", "composite_layup", "ASC", "Econoclave"),
            ("CNC Router", "cnc_machining", "Shopbot", "PRSalpha"),
        ],
    },
    {
        "name": "Bengaluru Electronics Workshop",
        "city": "Bengaluru",
        "region": "Karnataka",
        "country": "IN",
        "lat": 12.9716,
        "lon": 77.5946,
        "access_type": "Membership",
        "status": "Active",
        "processes": ["pcb_assembly", "3d_printing", "laser_cutting"],
        "equipment": [
            ("Reflow Oven", "pcb_assembly", "Puhui", "T962C"),
            ("Resin Printer", "3d_printing", "Elegoo", "Saturn 3"),
        ],
    },
    {
        "name": "Berlin Offene Werkstatt",
        "city": "Berlin",
        "region": "Berlin",
        "country": "DE",
        "lat": 52.5200,
        "lon": 13.4050,
        "access_type": "Public",
        # Deliberately not Active: the network surface renders a status axis,
        # and a single-status dataset never exercises it.
        "status": "Planned",
        "processes": ["woodworking", "assembly", "3d_printing"],
        "equipment": [
            ("3D Printer", "3d_printing", "Prusa", "MINI+"),
            ("CNC Router", "woodworking", "Stepcraft", "D840"),
        ],
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _write_record(directory: Path, record_id: str, payload: dict) -> None:
    """Write a record plus the sidecar the local storage provider expects."""
    directory.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    path = directory / f"{record_id}.json"
    path.write_text(body, encoding="utf-8")

    encoded = body.encode("utf-8")
    stamp = _now()
    meta = {
        "content_type": "application/json",
        "size": len(encoded),
        "created_at": stamp,
        "modified_at": stamp,
        "etag": hashlib.md5(encoded).hexdigest(),
        "version_id": None,
        "metadata": {"source": "seed_demo_data"},
    }
    path.with_suffix(".json.meta").write_text(json.dumps(meta), encoding="utf-8")


def build_okh(design: dict) -> dict:
    return {
        "id": demo_id("okh", design["title"]),
        "title": design["title"],
        "function": design["function"],
        "description": f"{design['function']} Seeded demo record.",
        "version": "1.0.0",
        "okhv": "OKH-LOSHv1.0",
        "documentation_language": "en",
        "keywords": design["keywords"],
        "license": {
            "hardware": design["license"],
            "documentation": design["license"],
            "software": None,
        },
        "licensor": {
            "name": design["licensor"],
            "email": None,
            "affiliation": None,
            "social": [],
        },
        "manufacturing_processes": design["processes"],
        "materials": design["materials"],
        "technical_specifications": {"category": design["category"]},
        "metadata": {"demo": True, "category": design["category"]},
        "contributors": [],
        "design_files": [],
        "manufacturing_files": [],
        "making_instructions": [],
        "operating_instructions": [],
        "repair_guides": [],
        "disassembly_guides": [],
        "parts": [],
        "sub_parts": [],
        "components": [],
        "tool_list": [],
        "tsdc": [],
        "standards_used": [],
        "publications": [],
        "software": [],
        "compatible_manifest_ids": [],
        "image": None,
        "project_link": None,
    }


def build_okw(facility: dict) -> dict:
    return {
        "id": demo_id("okw", facility["name"]),
        "name": facility["name"],
        "location": {
            "gps_coordinates": f"{facility['lat']}, {facility['lon']}",
            "coordinates": {"lat": facility["lat"], "lon": facility["lon"]},
            "city": facility["city"],
            "region": facility["region"],
            "country": facility["country"],
            "address": {
                "city": facility["city"],
                "region": facility["region"],
                "country": facility["country"],
            },
        },
        "facility_status": facility["status"],
        "access_type": facility["access_type"],
        "manufacturing_processes": facility["processes"],
        "equipment": [
            {
                "equipment_type": kind,
                "manufacturing_process": process,
                "make": make,
                "model": model,
            }
            for kind, process, make, model in facility["equipment"]
        ],
        "typical_materials": [],
        "certifications": [],
        "metadata": {"demo": True},
    }


def coverage() -> list[tuple[str, list[str]]]:
    """Which facilities can build each design (facility processes ⊇ design's)."""
    out = []
    for design in DESIGNS:
        needed = set(design["processes"])
        builders = [f["name"] for f in FACILITIES if needed <= set(f["processes"])]
        out.append((design["title"], builders))
    return out


def clear_demo_records(storage_dir: Path) -> int:
    """Remove only records this script wrote; leave everything else alone."""
    removed = 0
    wanted = {demo_id("okh", d["title"]) for d in DESIGNS}
    wanted |= {demo_id("okw", f["name"]) for f in FACILITIES}
    for sub in ("okh", "okw"):
        directory = storage_dir / sub
        if not directory.is_dir():
            continue
        for path in directory.glob("*.json"):
            if path.stem in wanted:
                path.with_suffix(".json.meta").unlink(missing_ok=True)
                path.unlink()
                removed += 1
    return removed


def seed(storage_dir: Path) -> dict:
    for design in DESIGNS:
        record = build_okh(design)
        _write_record(storage_dir / "okh", record["id"], record)
    for facility in FACILITIES:
        record = build_okw(facility)
        _write_record(storage_dir / "okw", record["id"], record)
    return {
        "designs": len(DESIGNS),
        "facilities": len(FACILITIES),
        "storage_dir": str(storage_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=_ROOT / "storage",
        help="Storage root to seed (default: ./storage)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Remove previously seeded demo records before writing",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print the dataset and its match coverage; write nothing",
    )
    args = parser.parse_args()

    if args.summary:
        print(f"{len(DESIGNS)} designs, {len(FACILITIES)} facilities\n")
        print("Match coverage (facilities that can build each design):")
        for title, builders in coverage():
            print(f"  {title:<28} {len(builders)}  {', '.join(builders) or '—'}")
        return 0

    if args.clear:
        print(f"cleared {clear_demo_records(args.storage_dir)} demo records")

    result = seed(args.storage_dir)
    print(
        f"seeded {result['designs']} designs and {result['facilities']} facilities "
        f"into {result['storage_dir']}"
    )
    unbuildable = [title for title, builders in coverage() if not builders]
    if unbuildable:
        print(f"WARNING: no facility can build: {', '.join(unbuildable)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
