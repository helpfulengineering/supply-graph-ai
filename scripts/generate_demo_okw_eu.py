#!/usr/bin/env python3
"""
Demo OKW Facility Generator - European Manufacturing Network

Generates a matched set of Open Know Where (OKW) facilities for every OKH design
currently held in remote blob storage.  For each design the script creates either:

  * A **single** OKW facility that covers all of the design's manufacturing
    requirements in one step, OR
  * A **set** of specialised OKW facilities that together form a valid
    multi-step manufacturing match (one facility per distinct process).

All generated facilities are located within European countries (EU region).

Validation
──────────
After generating facilities for each design the script runs the same composite
matching logic used by the API (find_composite_matches_with_manifest) to confirm
that the generated set achieves 100 % process coverage.  If coverage falls short
the script automatically adds remediation facilities for the missing processes and
re-validates.  Designs that cannot be fully covered after remediation are flagged
with a warning; their files are still written so they can be inspected manually.

Design-to-facility mapping rules
─────────────────────────────────
  • 0 processes detected   → 1 generic Assembly facility  (single-step)
  • 1 unique process       → 1 specialised facility       (single-step)
  • 2+ unique processes    → N specialised facilities,
                             one per process              (multi-step)

Data access
───────────
OKH manifests are fetched directly from remote blob storage via the
OKHService (the same back-end used by `ohm okh list-manifests`).

Usage
─────
  uv run python scripts/generate_demo_okw_eu.py
  uv run python scripts/generate_demo_okw_eu.py --output-dir ./my_demo_okw
  uv run python scripts/generate_demo_okw_eu.py --output-dir ./my_demo_okw --complexity complex
  uv run python scripts/generate_demo_okw_eu.py --output-dir ./my_demo_okw --validate
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path setup – mirrors generate_synthetic_data.py so the same imports work
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models.okh import OKHManifest
from core.models.okw import ManufacturingFacility
from src.core.taxonomy import taxonomy as process_taxonomy

# Re-use the generator and helpers from the existing synthetic data script.
# We intentionally import – not copy – so that any generator improvements
# are automatically picked up here.
from scripts.generate_synthetic_data import (
    OKWGenerator,
    save_record,
    validate_record,
)

# ---------------------------------------------------------------------------
# OKH manifest fetching via the storage service
# ---------------------------------------------------------------------------


async def _fetch_okh_manifests_async(page_size: int = 100) -> List[OKHManifest]:
    """
    Fetch all OKH manifests from remote blob storage using the OKHService.

    Uses the same code path as `ohm okh list-manifests` but calls the service
    directly so we can retrieve all records in a single request.
    """
    from src.cli.base import ensure_domains_registered
    from src.core.services.okh_service import OKHService

    await ensure_domains_registered()
    service = await OKHService.get_instance()

    manifests: List[OKHManifest] = []
    page = 1
    while True:
        result = await service.list(page=page, page_size=page_size)
        page_manifests, total = result if isinstance(result, tuple) else (result, 0)

        if not page_manifests:
            break

        manifests.extend(page_manifests)

        # Stop when we have fetched everything
        if len(manifests) >= total or len(page_manifests) < page_size:
            break
        page += 1

    return manifests


# ---------------------------------------------------------------------------
# Process normalisation helpers
# ---------------------------------------------------------------------------

# Fallback key → used when a process string can't be resolved through the
# taxonomy.  Assembly is a reasonable catch-all for unknown processes.
_FALLBACK_PROCESS_KEY = "ASM"


def _normalize_to_template_key(process: str) -> Optional[str]:
    """
    Normalise a raw process string to a key that exists in
    OKWGenerator.specialized_templates.

    Returns the TSDC code when available (e.g. "CNC"), otherwise the display
    name used as a template key (e.g. "Soldering", "Drilling").
    Returns None when the process cannot be resolved.
    """
    canonical_id = process_taxonomy.normalize(process)
    if canonical_id is None:
        return None
    tsdc = process_taxonomy.get_tsdc_code(canonical_id)
    if tsdc:
        return tsdc
    return process_taxonomy.get_display_name(canonical_id)


def _extract_all_process_requirements(manifest: OKHManifest) -> List[str]:
    """
    Extract every process requirement name from an OKH manifest using the
    same domain extractor that the matching service uses.

    This is the authoritative source of "what the OKH needs" – it pulls from
    manufacturing_processes, manufacturing_specs, parts[].tsdc, and
    sub_parts[].tsdc, matching exactly what find_composite_matches_with_manifest
    sees when it builds the requirement list.
    """
    try:
        from src.core.domains.manufacturing.okh_extractor import OKHExtractor

        extractor = OKHExtractor()
        result = extractor.extract_requirements(manifest.to_dict())
        if result.data and result.data.content:
            reqs = result.data.content.get("process_requirements", [])
            return [r.get("process_name", "") for r in reqs if r.get("process_name")]
    except Exception as exc:
        print(
            f"    ⚠  Could not extract requirements via extractor ({exc}); "
            "falling back to manufacturing_processes field"
        )

    # Fallback: use the raw manufacturing_processes list
    return list(manifest.manufacturing_processes or [])


def extract_process_keys(
    manifest: OKHManifest,
    valid_keys: frozenset,
) -> List[str]:
    """
    Return an ordered, deduplicated list of process template keys for the
    given manifest.  Only keys present in *valid_keys* are returned.
    """
    seen: Dict[str, int] = {}  # key → first-seen insertion order

    all_process_names = _extract_all_process_requirements(manifest)

    for proc in all_process_names:
        key = _normalize_to_template_key(proc)
        if key and key in valid_keys and key not in seen:
            seen[key] = len(seen)

    return list(seen.keys())


# ---------------------------------------------------------------------------
# Match validation helpers
# ---------------------------------------------------------------------------


async def _validate_match_coverage(
    manifest: OKHManifest,
    facilities: List[ManufacturingFacility],
) -> Tuple[float, List[str]]:
    """
    Run the same composite matching logic used by the API to check whether
    the provided facilities completely cover the OKH manifest's requirements.

    Returns:
        (coverage_ratio, coverage_gaps) where coverage_ratio is in [0, 1]
        and coverage_gaps is the list of uncovered process names.
        Returns (1.0, []) when all requirements are satisfied (including
        the vacuous case of zero requirements).
    """
    from src.core.services.matching_service import MatchingService

    # If the manifest has no process requirements there is nothing to cover –
    # treat this as a valid (trivially complete) match.
    raw_reqs = _extract_all_process_requirements(manifest)
    if not raw_reqs:
        return 1.0, []

    # Use a generous facility cap so greedy set-cover can find a full solution.
    ms = await MatchingService.get_instance()
    solutions = await ms.find_composite_matches_with_manifest(
        okh_manifest=manifest,
        facilities=facilities,
        max_facilities_per_solution=max(10, len(facilities)),
    )

    if not solutions:
        return 0.0, []

    # Return the solution with the highest coverage ratio.
    best = max(solutions, key=lambda s: s.metadata.get("coverage_ratio", 0.0))
    ratio = best.metadata.get("coverage_ratio", 0.0)
    gaps = best.metadata.get("coverage_gaps", [])
    return ratio, gaps


def _patch_facility_processes(
    facility: ManufacturingFacility,
    raw_process_name: str,
) -> None:
    """
    Ensure *raw_process_name* appears in facility.manufacturing_processes.

    The matching service normalises both sides independently, but there can be
    asymmetry when the OKH uses a Wikipedia URL that the taxonomy does not
    recognise (so the requirement becomes a raw slug) while the facility
    capability is normalised to a canonical ID.  Adding the exact raw string
    from the OKH guarantees a direct-match hit.
    """
    current = list(facility.manufacturing_processes or [])
    if raw_process_name and raw_process_name not in current:
        current.append(raw_process_name)
        facility.manufacturing_processes = current


# ---------------------------------------------------------------------------
# Per-design facility generation
# ---------------------------------------------------------------------------

MatchType = str  # "single" | "multi-step"


def _generate_raw_facilities(
    manifest: OKHManifest,
    generator: OKWGenerator,
) -> Tuple[List[ManufacturingFacility], MatchType, List[str]]:
    """
    Generate OKW facilities for a design and patch them with the exact
    process names that the matching service will look for.

    Returns:
        (facilities, match_type, raw_process_names)
        raw_process_names is the authoritative list from the OKH extractor.
    """
    valid_keys = frozenset(generator.specialized_templates.keys())
    raw_process_names = _extract_all_process_requirements(manifest)
    process_keys = extract_process_keys(manifest, valid_keys)

    if not process_keys:
        # No recognised processes – create a generic Assembly facility.
        facility = generator.generate_specialized_facility(
            _FALLBACK_PROCESS_KEY, facility_index=1
        )
        # Patch with any raw process names so the matcher can find a match.
        for name in raw_process_names:
            _patch_facility_processes(facility, name)
        return [facility], "single", raw_process_names

    if len(process_keys) == 1:
        facility = generator.generate_specialized_facility(
            process_keys[0], facility_index=1
        )
        for name in raw_process_names:
            _patch_facility_processes(facility, name)
        return [facility], "single", raw_process_names

    # Multiple processes → one specialised facility per process key.
    # Build a mapping: process_key → [raw_process_names that resolve to it]
    key_to_raws: Dict[str, List[str]] = {k: [] for k in process_keys}
    for raw in raw_process_names:
        key = _normalize_to_template_key(raw)
        if key and key in key_to_raws:
            key_to_raws[key].append(raw)

    facilities = []
    for idx, key in enumerate(process_keys, start=1):
        f = generator.generate_specialized_facility(key, facility_index=idx)
        for raw in key_to_raws.get(key, []):
            _patch_facility_processes(f, raw)
        facilities.append(f)

    return facilities, "multi-step", raw_process_names


async def generate_and_validate_facilities(
    manifest: OKHManifest,
    generator: OKWGenerator,
    max_remediation_rounds: int = 2,
) -> Tuple[List[ManufacturingFacility], MatchType, bool]:
    """
    Generate OKW facilities for an OKH design and validate that they
    achieve 100 % process coverage using the composite matching service.

    If coverage is incomplete, the function attempts up to
    *max_remediation_rounds* remediation rounds.  In each round a new
    facility is added for every uncovered process.  The facilities are
    always returned even if full coverage could not be achieved – the
    caller receives a boolean flag indicating success.

    Returns:
        (facilities, match_type, coverage_complete)
    """
    valid_keys = frozenset(generator.specialized_templates.keys())
    facilities, match_type, raw_process_names = _generate_raw_facilities(
        manifest, generator
    )

    # ------------------------------------------------------------------
    # Validation + remediation loop
    # ------------------------------------------------------------------
    coverage, gaps = await _validate_match_coverage(manifest, facilities)

    for _round in range(max_remediation_rounds):
        if coverage >= 1.0 or not gaps:
            break

        print(
            f"    ↺  Coverage {coverage:.0%} – adding remediation facilities "
            f"for: {gaps}"
        )

        for gap_process in gaps:
            # Try to find a template key for the gap process; fall back to ASM.
            key = _normalize_to_template_key(gap_process)
            if not key or key not in valid_keys:
                key = _FALLBACK_PROCESS_KEY

            remediation = generator.generate_specialized_facility(
                key, facility_index=len(facilities) + 1
            )
            # Patch with the exact gap process name so the matcher finds it.
            _patch_facility_processes(remediation, gap_process)
            facilities.append(remediation)
            match_type = "multi-step"

        coverage, gaps = await _validate_match_coverage(manifest, facilities)

    coverage_complete = coverage >= 1.0
    return facilities, match_type, coverage_complete


# ---------------------------------------------------------------------------
# File saving helpers
# ---------------------------------------------------------------------------


def _safe_name(text: str, max_len: int = 40) -> str:
    """Convert arbitrary text to a safe filename fragment."""
    safe = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "" for c in (text or "unknown")
    ).strip()
    return safe.replace(" ", "-").lower()[:max_len]


def save_facilities(
    facilities: List[ManufacturingFacility],
    match_type: MatchType,
    design_title: str,
    output_dir: str,
    global_index: int,
    validate: bool = False,
) -> List[str]:
    """
    Save a list of facilities to *output_dir*.

    For multi-step sets the files are named with a step suffix so the
    relationship between facilities is obvious.  Returns the list of file
    paths written.
    """
    title_slug = _safe_name(design_title)
    saved: List[str] = []

    for step, facility in enumerate(facilities, start=1):
        # Optionally validate schema
        if validate and not validate_record(facility):
            print(f"    ⚠  Facility {step} failed schema validation – skipping")
            continue

        # Build a descriptive name so the file is self-explanatory
        process_slug = _safe_name(
            facility.name.replace("Facility", "").replace("  ", " ").strip(), 30
        )
        if match_type == "multi-step":
            facility.name = f"{facility.name} (for {design_title[:30]})"
            filename_hint = f"{title_slug}-step{step:02d}-{process_slug}"
        else:
            filename_hint = f"{title_slug}-{process_slug}"

        filepath = save_record(facility, output_dir, global_index + step - 1)
        # Rename to include the design context
        new_path = os.path.join(
            output_dir,
            f"{filename_hint}-okw.json",
        )
        if filepath != new_path:
            os.rename(filepath, new_path)
            filepath = new_path

        saved.append(filepath)

    return saved


# ---------------------------------------------------------------------------
# Main (async)
# ---------------------------------------------------------------------------


async def _run(args: argparse.Namespace) -> None:
    """Async entry-point – fetches manifests, generates, validates, and saves."""

    print("━" * 72)
    print("  Demo OKW Generator – European Manufacturing Network")
    print("━" * 72)
    print()

    # ------------------------------------------------------------------
    # Step 1: Fetch all OKH manifests from remote blob storage
    # ------------------------------------------------------------------
    print("Fetching OKH manifests from remote blob storage …")
    manifests = await _fetch_okh_manifests_async()

    if not manifests:
        print("ERROR: No OKH manifests found in storage. Aborting.")
        sys.exit(1)

    print(f"  Found {len(manifests)} OKH manifest(s).\n")

    # ------------------------------------------------------------------
    # Step 2: Create the EU OKW generator (all facilities in Europe)
    # ------------------------------------------------------------------
    generator = OKWGenerator(complexity=args.complexity, region="EU")
    valid_keys = frozenset(generator.specialized_templates.keys())

    # ------------------------------------------------------------------
    # Step 3: Plan / generate / validate one set per design
    # ------------------------------------------------------------------
    if not args.dry_run:
        os.makedirs(args.output_dir, exist_ok=True)

    total_files = 0
    single_count = 0
    multi_count = 0
    validation_failures: List[str] = []
    global_index = 1

    print(f"{'Design':<50}  {'Type':<12}  {'Facilities'}")
    print("-" * 72)

    for manifest in manifests:
        title = manifest.title or str(manifest.id)[:16]
        process_keys = extract_process_keys(manifest, valid_keys)
        raw_reqs = _extract_all_process_requirements(manifest)

        # Determine match type for display
        if not process_keys:
            match_preview = "single"
            facility_preview = f"1 × ASM (fallback)"
        elif len(process_keys) == 1:
            match_preview = "single"
            facility_preview = f"1 × {process_keys[0]}"
        else:
            match_preview = "multi-step"
            facility_preview = f"{len(process_keys)} × [{', '.join(process_keys)}]"

        n_reqs = len(raw_reqs)
        print(
            f"{title[:49]:<50}  {match_preview:<12}  "
            f"{facility_preview}  ({n_reqs} req{'s' if n_reqs != 1 else ''})"
        )

        if args.dry_run:
            continue

        # ------------------------------------------------------------------
        # Generate facilities and validate match coverage
        # ------------------------------------------------------------------
        facilities, match_type, coverage_ok = await generate_and_validate_facilities(
            manifest, generator
        )

        if coverage_ok:
            print(
                f"    ✓  Match validated – {len(facilities)} facility(ies) cover all requirements"
            )
        else:
            print(
                f"    ✗  Coverage incomplete after remediation – "
                f"saving {len(facilities)} file(s) for manual review"
            )
            validation_failures.append(title)

        # ------------------------------------------------------------------
        # Save to disk
        # ------------------------------------------------------------------
        saved_paths = save_facilities(
            facilities=facilities,
            match_type=match_type,
            design_title=title,
            output_dir=args.output_dir,
            global_index=global_index,
            validate=args.validate,
        )

        n_saved = len(saved_paths)
        global_index += n_saved
        total_files += n_saved

        if match_type == "single":
            single_count += 1
        else:
            multi_count += 1

        for path in saved_paths:
            print(f"    → {os.path.relpath(path)}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("━" * 72)
    if args.dry_run:
        print("  DRY RUN complete – no files were written.")
    else:
        print(f"  Generation complete!")
        print(f"  OKH designs processed   : {len(manifests)}")
        print(f"    Single-step matches    : {single_count}")
        print(f"    Multi-step matches     : {multi_count}")
        print(f"  OKW files written        : {total_files}")
        print(f"  Output directory         : {os.path.abspath(args.output_dir)}")

        if validation_failures:
            print()
            print(
                f"  ⚠  {len(validation_failures)} design(s) with incomplete coverage:"
            )
            for name in validation_failures:
                print(f"     • {name}")
            print(
                "  Check that the OKH processes are covered by a template in "
                "OKWGenerator.specialized_templates, or upload additional facilities "
                "manually."
            )
        else:
            print(f"  ✓  All designs validated – complete match coverage confirmed.")

    print("━" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate matched OKW facilities for every OKH design in "
            "remote storage. All facilities are located in European countries."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output-dir",
        default="./demo_okw_eu",
        help="Output directory for generated OKW files (default: ./demo_okw_eu)",
    )
    parser.add_argument(
        "--complexity",
        choices=["minimal", "complex", "mixed"],
        default="mixed",
        help="Complexity level for generated facility data (default: mixed)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate each generated OKW record against the schema before saving",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generation plan without writing any files",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
