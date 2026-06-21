"""CLI commands for managing AssetRecord — physical state of device units."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

import click

from ..core.services.asset_service import AssetService
from .base import CLIContext, SmartCommand
from .decorators import async_command


@click.group("asset")
def asset_group() -> None:
    """Manage asset records — physical state of device units in the field.

    An asset record links a specific physical unit (identified by its asset tag)
    to an OKH manifest (the design) and tracks the condition of each component
    observed during triage.

    \b
    Examples:
      ohm asset create <manifest-id> --asset-tag SN-001
      ohm asset triage <asset-id> --component "Blood pump" --condition damaged
      ohm asset list --manifest-id <manifest-id> --harvest-viable
    """


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@asset_group.command("create")
@click.argument("manifest_id")
@click.option(
    "--asset-tag",
    required=True,
    help="Facility-assigned identifier (serial, barcode, …)",
)
@click.option("--location", default=None, help="Where this unit is deployed")
@async_command
@click.pass_context
async def create_cmd(ctx, manifest_id, asset_tag, location):
    """Create an asset record for a physical unit.

    \b
    Examples:
      ohm asset create <manifest-id> --asset-tag SN-001
      ohm asset create <manifest-id> --asset-tag ASSET-42 --location "ICU Bay 3"
    """
    cli_ctx = ctx.obj
    payload: Dict[str, Any] = {
        "manifest_id": manifest_id,
        "asset_tag": asset_tag,
        "location": location,
    }

    async def http_create():
        async with cli_ctx.api_client.get_client() as client:
            r = await client.post("/api/asset/", json=payload)
            r.raise_for_status()
            return r.json()

    async def fallback_create():
        svc = await AssetService.get_instance()
        record = await svc.create(payload)
        return record.to_dict()

    command = SmartCommand(cli_ctx)
    data = await command.execute_with_fallback(http_create, fallback_create)
    cli_ctx.log(f"Created asset {data['id']} (tag: {data['asset_tag']})", "success")
    if data.get("location"):
        cli_ctx.log(f"  Location: {data['location']}", "info")


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


@asset_group.command("get")
@click.argument("asset_id")
@async_command
@click.pass_context
async def get_cmd(ctx, asset_id):
    """Get an asset record by ID.

    \b
    Examples:
      ohm asset get <asset-id>
    """
    cli_ctx = ctx.obj

    async def http_get():
        async with cli_ctx.api_client.get_client() as client:
            r = await client.get(f"/api/asset/{asset_id}")
            r.raise_for_status()
            return r.json()

    async def fallback_get():
        svc = await AssetService.get_instance()
        record = await svc.get(UUID(asset_id))
        if record is None:
            raise click.ClickException(f"Asset {asset_id!r} not found.")
        return record.to_dict()

    command = SmartCommand(cli_ctx)
    data = await command.execute_with_fallback(http_get, fallback_get)
    _print_asset(cli_ctx, data)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@asset_group.command("list")
@click.option("--manifest-id", default=None, help="Filter to this manifest UUID")
@click.option(
    "--harvest-viable",
    is_flag=True,
    default=False,
    help="Show only assets with harvestable components",
)
@click.option("--output", "-o", default=None, help="Write results to a JSON file")
@async_command
@click.pass_context
async def list_cmd(ctx, manifest_id, harvest_viable, output):
    """List asset records, optionally filtered.

    \b
    Examples:
      ohm asset list
      ohm asset list --manifest-id <uuid>
      ohm asset list --harvest-viable
    """
    cli_ctx = ctx.obj

    async def http_list():
        params: Dict[str, Any] = {}
        if manifest_id:
            params["manifest_id"] = manifest_id
        if harvest_viable:
            params["harvest_viable"] = "true"
        async with cli_ctx.api_client.get_client() as client:
            r = await client.get("/api/asset/", params=params)
            r.raise_for_status()
            return r.json()

    async def fallback_list():
        svc = await AssetService.get_instance()
        records = await svc.list(manifest_id=manifest_id)
        if harvest_viable:
            filtered = []
            for rec in records:
                viable = [cs for cs in rec.component_states if cs.harvest_viable]
                if viable:
                    rec.component_states = viable
                    filtered.append(rec)
            records = filtered
        assets = [r.to_dict() for r in records]
        return {"assets": assets, "total": len(assets)}

    command = SmartCommand(cli_ctx)
    data = await command.execute_with_fallback(http_list, fallback_list)
    assets = data.get("assets", [])
    cli_ctx.log(f"{data.get('total', len(assets))} asset(s) found.", "success")
    for a in assets:
        states_n = len(a.get("component_states", []))
        cli_ctx.log(
            f"  [{a['id'][:8]}…] tag={a['asset_tag']}  manifest={a['manifest_id'][:8]}…"
            f"  states={states_n}",
            "info",
        )
    if output:
        Path(output).write_text(json.dumps(data, indent=2))
        cli_ctx.log(f"Written to {output}", "info")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@asset_group.command("update")
@click.argument("asset_id")
@click.option("--asset-tag", default=None, help="New asset tag")
@click.option("--location", default=None, help="New location")
@click.option("--triage-notes", default=None, help="Update triage notes")
@async_command
@click.pass_context
async def update_cmd(ctx, asset_id, asset_tag, location, triage_notes):
    """Update top-level fields on an asset record.

    \b
    Examples:
      ohm asset update <asset-id> --location "Ward 4B"
      ohm asset update <asset-id> --triage-notes "Cleared for reuse after repairs"
    """
    cli_ctx = ctx.obj
    payload: Dict[str, Any] = {}
    if asset_tag:
        payload["asset_tag"] = asset_tag
    if location:
        payload["location"] = location
    if triage_notes:
        payload["triage_notes"] = triage_notes

    async def http_update():
        async with cli_ctx.api_client.get_client() as client:
            r = await client.put(f"/api/asset/{asset_id}", json=payload)
            r.raise_for_status()
            return r.json()

    async def fallback_update():
        svc = await AssetService.get_instance()
        record = await svc.get(UUID(asset_id))
        if record is None:
            raise click.ClickException(f"Asset {asset_id!r} not found.")
        if asset_tag:
            record.asset_tag = asset_tag
        if location:
            record.location = location
        if triage_notes:
            record.triage_notes = triage_notes
        updated = await svc.update(UUID(asset_id), record.to_dict())
        return updated.to_dict()

    command = SmartCommand(cli_ctx)
    data = await command.execute_with_fallback(http_update, fallback_update)
    cli_ctx.log(f"Updated asset {data['id']}", "success")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@asset_group.command("delete")
@click.argument("asset_id")
@click.confirmation_option(prompt="Delete this asset record?")
@async_command
@click.pass_context
async def delete_cmd(ctx, asset_id):
    """Delete an asset record.

    \b
    Examples:
      ohm asset delete <asset-id>
    """
    cli_ctx = ctx.obj

    async def http_delete():
        async with cli_ctx.api_client.get_client() as client:
            r = await client.delete(f"/api/asset/{asset_id}")
            r.raise_for_status()
            return r.json()

    async def fallback_delete():
        svc = await AssetService.get_instance()
        deleted = await svc.delete(UUID(asset_id))
        if not deleted:
            raise click.ClickException(f"Asset {asset_id!r} not found.")
        return {"success": True}

    command = SmartCommand(cli_ctx)
    await command.execute_with_fallback(http_delete, fallback_delete)
    cli_ctx.log(f"Deleted asset {asset_id}", "success")


# ---------------------------------------------------------------------------
# triage
# ---------------------------------------------------------------------------


@asset_group.command("triage")
@click.argument("asset_id")
@click.option(
    "--states",
    "states_file",
    default=None,
    type=click.Path(exists=True),
    help="JSON file with component_states array",
)
@click.option(
    "--component", default=None, help="Component name (single-component mode)"
)
@click.option(
    "--condition",
    type=click.Choice(["intact", "damaged", "missing", "unknown"]),
    default=None,
    help="Observed condition (required with --component)",
)
@click.option(
    "--repair-feasible/--no-repair-feasible",
    default=None,
    help="Can this component be repaired in place?",
)
@click.option(
    "--harvest-viable/--no-harvest-viable",
    default=None,
    help="Can this component be harvested for use elsewhere?",
)
@click.option(
    "--source-required/--no-source-required",
    default=None,
    help="Must a replacement be sourced?",
)
@click.option("--notes", default=None, help="Technician notes for this component")
@click.option("--assessed-by", default=None, help="Who performed the assessment")
@click.option(
    "--triage-notes", default=None, help="Overall notes for this triage session"
)
@async_command
@click.pass_context
async def triage_cmd(
    ctx,
    asset_id,
    states_file,
    component,
    condition,
    repair_feasible,
    harvest_viable,
    source_required,
    notes,
    assessed_by,
    triage_notes,
):
    """Record triage results for an asset.

    Use --states to batch-load from a JSON file, or --component + --condition
    to record a single component inline.

    \b
    Examples:
      ohm asset triage <asset-id> --states triage.json
      ohm asset triage <asset-id> --component "Blood pump" --condition damaged \\
          --no-repair-feasible --no-harvest-viable --source-required
    """
    cli_ctx = ctx.obj

    if states_file:
        raw_states = json.loads(Path(states_file).read_text())
        if isinstance(raw_states, dict):
            raw_states = raw_states.get("component_states", [])
    elif component:
        if not condition:
            raise click.UsageError("--condition is required with --component")
        state: Dict[str, Any] = {"component_name": component, "condition": condition}
        if repair_feasible is not None:
            state["repair_feasible"] = repair_feasible
        if harvest_viable is not None:
            state["harvest_viable"] = harvest_viable
        if source_required is not None:
            state["source_required"] = source_required
        if notes:
            state["notes"] = notes
        if assessed_by:
            state["assessed_by"] = assessed_by
        raw_states = [state]
    else:
        raise click.UsageError(
            "Provide either --states <file> or --component + --condition"
        )

    payload: Dict[str, Any] = {"component_states": raw_states}
    if triage_notes:
        payload["triage_notes"] = triage_notes

    async def http_triage():
        async with cli_ctx.api_client.get_client() as client:
            r = await client.post(f"/api/asset/{asset_id}/triage", json=payload)
            r.raise_for_status()
            return r.json()

    async def fallback_triage():
        from ..core.models.asset import ComponentState as _CS

        svc = await AssetService.get_instance()
        states = [_CS.from_dict(s) for s in raw_states]
        record = await svc.record_triage(
            UUID(asset_id), states, payload.get("triage_notes")
        )
        return record.to_dict()

    command = SmartCommand(cli_ctx)
    data = await command.execute_with_fallback(http_triage, fallback_triage)
    cli_ctx.log(
        f"Triage recorded for asset {data['id']} "
        f"({len(data.get('component_states', []))} component(s)).",
        "success",
    )
    if data.get("last_triaged_at"):
        cli_ctx.log(f"  Last triaged: {data['last_triaged_at']}", "info")


# ---------------------------------------------------------------------------
# Display helper
# ---------------------------------------------------------------------------


def _print_asset(cli_ctx: CLIContext, data: Dict[str, Any]) -> None:
    cli_ctx.log(f"Asset {data['id']}", "success")
    cli_ctx.log(f"  Tag        : {data['asset_tag']}", "info")
    cli_ctx.log(f"  Manifest   : {data['manifest_id']}", "info")
    if data.get("location"):
        cli_ctx.log(f"  Location   : {data['location']}", "info")
    if data.get("last_triaged_at"):
        cli_ctx.log(f"  Last triage: {data['last_triaged_at']}", "info")
    if data.get("triage_notes"):
        cli_ctx.log(f"  Notes      : {data['triage_notes']}", "info")
    states = data.get("component_states", [])
    if states:
        cli_ctx.log(f"\n  Component states ({len(states)}):", "info")
        for cs in states:
            flags = []
            if cs.get("repair_feasible"):
                flags.append("repair-feasible")
            if cs.get("harvest_viable"):
                flags.append("harvest-viable")
            if cs.get("source_required"):
                flags.append("source-required")
            flag_str = f"  [{', '.join(flags)}]" if flags else ""
            cli_ctx.log(
                f"    {cs['component_name']}: {cs['condition']}{flag_str}", "info"
            )
