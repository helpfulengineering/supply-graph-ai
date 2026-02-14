"""
Taxonomy management commands for OHM CLI.

These commands provide local management of the canonical process taxonomy:
listing, validating, and reloading process definitions from YAML.

These commands operate directly on the local taxonomy module and do NOT
require a running API server.
"""

import json
from pathlib import Path
from typing import Optional

import click

from ..core.taxonomy import (
    DEFAULT_TAXONOMY_PATH,
    ProcessTaxonomy,
    load_from_yaml,
    taxonomy,
    validate_definitions,
)


@click.group()
def taxonomy_group():
    """
    Process taxonomy management commands.

    Manage the canonical manufacturing process taxonomy that powers
    process normalization, matching, and validation across OHM.

    The taxonomy is defined in a YAML file and can be validated,
    listed, and reloaded at runtime.

    Examples:
      # List all processes in the taxonomy
      ohm taxonomy list

      # Validate the default taxonomy YAML
      ohm taxonomy validate

      # Validate a custom YAML file
      ohm taxonomy validate /path/to/custom.yaml

      # Reload taxonomy from the default YAML
      ohm taxonomy reload

      # Reload from a specific file
      ohm taxonomy reload /path/to/custom.yaml
    """
    pass


@taxonomy_group.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--tsdc-only", is_flag=True, help="Show only processes with TSDC codes")
@click.option("--roots-only", is_flag=True, help="Show only root processes (no parent)")
def taxonomy_list(output_json: bool, tsdc_only: bool, roots_only: bool):
    """List all processes in the current taxonomy.

    Shows canonical ID, display name, TSDC code, and parent for each process.
    """
    all_ids = sorted(taxonomy.get_all_canonical_ids())

    if output_json:
        entries = []
        for cid in all_ids:
            defn = taxonomy.get_definition(cid)
            if not defn:
                continue
            if tsdc_only and not defn.tsdc_code:
                continue
            if roots_only and defn.parent:
                continue
            entries.append(
                {
                    "canonical_id": defn.canonical_id,
                    "display_name": defn.display_name,
                    "tsdc_code": defn.tsdc_code,
                    "parent": defn.parent,
                    "aliases": sorted(defn.aliases),
                }
            )
        click.echo(json.dumps(entries, indent=2))
        return

    # Text output
    source = taxonomy._source_path or "built-in definitions"
    click.echo(f"Process Taxonomy ({len(all_ids)} processes)")
    click.echo(f"Source: {source}")
    click.echo()

    # Table header
    click.echo(f"  {'CANONICAL ID':<30} {'DISPLAY NAME':<25} {'TSDC':<8} {'PARENT'}")
    click.echo(f"  {'-' * 30} {'-' * 25} {'-' * 8} {'-' * 20}")

    count = 0
    for cid in all_ids:
        defn = taxonomy.get_definition(cid)
        if not defn:
            continue
        if tsdc_only and not defn.tsdc_code:
            continue
        if roots_only and defn.parent:
            continue

        tsdc = defn.tsdc_code or ""
        parent = defn.parent or ""
        click.echo(f"  {cid:<30} {defn.display_name:<25} {tsdc:<8} {parent}")
        count += 1

    click.echo()
    click.echo(f"  {count} process(es) displayed")


@taxonomy_group.command("validate")
@click.argument("file", type=click.Path(exists=False), required=False)
def taxonomy_validate(file: Optional[str]):
    """Validate a taxonomy YAML file without applying it.

    If FILE is not provided, validates the default taxonomy YAML at
    src/config/taxonomy/processes.yaml.

    Runs all integrity checks: unique IDs, valid parents, no cycles,
    snake_case format, and no alias collisions.
    """
    path = Path(file) if file else DEFAULT_TAXONOMY_PATH

    click.echo(f"Validating: {path}")
    click.echo()

    # Check file exists
    if not path.exists():
        click.echo(f"  ERROR: File not found: {path}", err=True)
        raise SystemExit(1)

    # Try loading
    try:
        definitions = load_from_yaml(path)
        click.echo(f"  Loaded {len(definitions)} process definitions")
    except Exception as e:
        click.echo(f"  ERROR: Failed to parse YAML: {e}", err=True)
        raise SystemExit(1)

    # Validate
    errors = validate_definitions(definitions)
    if errors:
        click.echo(f"  FAILED: {len(errors)} validation error(s):")
        for err in errors:
            click.echo(f"    - {err}")
        raise SystemExit(1)

    # Also check that it produces a working taxonomy
    try:
        test_taxonomy = ProcessTaxonomy(definitions)
        # Quick smoke test
        all_ids = test_taxonomy.get_all_canonical_ids()
        click.echo(f"  Canonical IDs:  {len(all_ids)}")

        tsdc_count = sum(1 for cid in all_ids if test_taxonomy.get_tsdc_code(cid))
        click.echo(f"  With TSDC code: {tsdc_count}")

        root_count = sum(1 for cid in all_ids if not test_taxonomy.get_parent(cid))
        click.echo(f"  Root processes: {root_count}")

        child_count = len(all_ids) - root_count
        click.echo(f"  Child processes: {child_count}")
    except Exception as e:
        click.echo(f"  ERROR: Failed to build taxonomy: {e}", err=True)
        raise SystemExit(1)

    click.echo()
    click.echo("  PASSED: Taxonomy is valid")


@taxonomy_group.command("reload")
@click.argument("file", type=click.Path(exists=False), required=False)
@click.option("--dry-run", is_flag=True, help="Validate only, do not apply")
def taxonomy_reload(file: Optional[str], dry_run: bool):
    """Reload the taxonomy from a YAML file.

    If FILE is not provided, reloads from the default YAML at
    src/config/taxonomy/processes.yaml.

    The reload is atomic: if validation fails, the current taxonomy
    is preserved.
    """
    path = Path(file) if file else DEFAULT_TAXONOMY_PATH

    click.echo(f"Reloading taxonomy from: {path}")

    if not path.exists():
        click.echo(f"  ERROR: File not found: {path}", err=True)
        raise SystemExit(1)

    if dry_run:
        click.echo("  (dry-run mode: validating only)")
        try:
            definitions = load_from_yaml(path)
            errors = validate_definitions(definitions)
            if errors:
                click.echo(f"  FAILED: {len(errors)} validation error(s):")
                for err in errors:
                    click.echo(f"    - {err}")
                raise SystemExit(1)
            click.echo(f"  Would load {len(definitions)} processes")
            click.echo("  PASSED: File is valid (no changes applied)")
        except SystemExit:
            raise
        except Exception as e:
            click.echo(f"  ERROR: {e}", err=True)
            raise SystemExit(1)
        return

    # Actual reload
    old_count = len(taxonomy.get_all_canonical_ids())

    try:
        result = taxonomy.reload(path)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"  ERROR: {e}", err=True)
        click.echo("  Taxonomy was NOT changed.")
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"  ERROR: Unexpected error: {e}", err=True)
        click.echo("  Taxonomy was NOT changed.")
        raise SystemExit(1)

    click.echo()
    click.echo(f"  Version:  {result['version']}")
    click.echo(f"  Source:   {result['source']}")
    click.echo(f"  Total:    {result['total']} processes (was {old_count})")

    if result["added"]:
        click.echo(f"  Added:    {', '.join(result['added'])}")
    if result["removed"]:
        click.echo(f"  Removed:  {', '.join(result['removed'])}")
    if not result["added"] and not result["removed"]:
        click.echo("  Changes:  none (taxonomy unchanged)")

    click.echo()
    click.echo("  Taxonomy reloaded successfully")
