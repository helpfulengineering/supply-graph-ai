"""File type taxonomy management commands for OHM CLI."""

import json
from pathlib import Path
from typing import Optional

import click

from src.core.taxonomy.file_type_taxonomy import (
    DEFAULT_FILE_TYPES_PATH,
    FileTypeTaxonomy,
    file_type_taxonomy,
    load_from_yaml,
    validate_definitions,
)


@click.group()
def file_types_group() -> None:
    """File type taxonomy management commands."""
    pass


@file_types_group.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def file_types_list(output_json: bool) -> None:
    """List all file types in the current taxonomy."""
    all_ids = sorted(file_type_taxonomy.get_all_canonical_ids())

    if output_json:
        entries = []
        for cid in all_ids:
            defn = file_type_taxonomy.get_definition(cid)
            if not defn:
                continue
            entries.append(
                {
                    "canonical_id": defn.canonical_id,
                    "display_name": defn.display_name,
                    "parent": defn.parent,
                    "extensions": sorted(defn.extensions),
                    "okh_role": defn.okh_role,
                    "render_tier": defn.render_tier,
                }
            )
        click.echo(json.dumps(entries, indent=2))
        return

    source = file_type_taxonomy._source_path or "built-in definitions"
    click.echo(f"File Type Taxonomy ({len(all_ids)} types)")
    click.echo(f"Source: {source}")
    click.echo()
    click.echo(
        f"  {'CANONICAL ID':<24} {'DISPLAY NAME':<20} {'RENDER TIER':<16} {'OKH ROLE'}"
    )
    click.echo(f"  {'-' * 24} {'-' * 20} {'-' * 16} {'-' * 16}")

    for cid in all_ids:
        defn = file_type_taxonomy.get_definition(cid)
        if not defn:
            continue
        click.echo(
            f"  {cid:<24} {defn.display_name:<20} {defn.render_tier:<16} {defn.okh_role}"
        )


@file_types_group.command("validate")
@click.argument("file", type=click.Path(exists=False), required=False)
def file_types_validate(file: Optional[str]) -> None:
    """Validate a file type taxonomy YAML file."""
    path = Path(file) if file else DEFAULT_FILE_TYPES_PATH
    click.echo(f"Validating: {path}")

    if not path.exists():
        click.echo(f"  ERROR: File not found: {path}", err=True)
        raise SystemExit(1)

    try:
        definitions = load_from_yaml(path)
    except Exception as e:
        click.echo(f"  ERROR: Failed to parse YAML: {e}", err=True)
        raise SystemExit(1)

    errors = validate_definitions(definitions)
    if errors:
        click.echo(f"  FAILED: {len(errors)} validation error(s):")
        for err in errors:
            click.echo(f"    - {err}")
        raise SystemExit(1)

    try:
        FileTypeTaxonomy(definitions)
    except Exception as e:
        click.echo(f"  ERROR: Failed to build taxonomy: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"  Loaded {len(definitions)} file type definitions")
    click.echo("  PASSED: Taxonomy is valid")
