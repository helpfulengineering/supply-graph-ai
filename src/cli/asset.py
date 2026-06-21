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
# triage-report
# ---------------------------------------------------------------------------

_ACTION_LABELS: Dict[str, str] = {
    "assess": "  ASSESS     ",
    "no_action": "  OK         ",
    "repair_in_place": "  REPAIR     ",
    "harvest": "  HARVEST    ",
    "source_new": "  SOURCE NEW ",
    "decommission": "  DECOMMISION",
}


@asset_group.command("triage-report")
@click.argument("asset_id")
@click.option("--output", "-o", default=None, help="Write report JSON to a file")
@async_command
@click.pass_context
async def triage_report_cmd(ctx, asset_id, output):
    """Generate a repair triage report for an asset.

    Joins the asset's observed component states with the design's repair flags
    (replaceable / salvageable / consumable) to produce a per-component
    recommended action.

    \b
    Examples:
      ohm asset triage-report <asset-id>
      ohm asset triage-report <asset-id> --output report.json
    """
    cli_ctx = ctx.obj

    async def http_report():
        async with cli_ctx.api_client.get_client() as client:
            r = await client.get(f"/api/asset/{asset_id}/triage-report")
            r.raise_for_status()
            return r.json()

    async def fallback_report():
        svc = await AssetService.get_instance()
        report = await svc.generate_triage_report(UUID(asset_id))
        return report.to_dict()

    command = SmartCommand(cli_ctx)
    data = await command.execute_with_fallback(http_report, fallback_report)

    s = data.get("summary", {})
    cli_ctx.log(
        f"Triage report for asset {data['asset_id'][:8]}…  tag={data['asset_tag']}",
        "success",
    )
    if data.get("last_triaged_at"):
        cli_ctx.log(f"  Last triaged: {data['last_triaged_at']}", "info")
    cli_ctx.log(
        f"  Summary: {s.get('total_components', 0)} components — "
        f"assess={s.get('needs_assessment', 0)}  "
        f"repair={s.get('repair_in_place', 0)}  "
        f"harvest={s.get('harvest', 0)}  "
        f"source_new={s.get('source_new', 0)}  "
        f"ok={s.get('no_action', 0)}  "
        f"decommission={s.get('decommission', 0)}",
        "info",
    )
    cli_ctx.log("", "info")
    for item in data.get("items", []):
        label = _ACTION_LABELS.get(
            item["recommended_action"], f"  {item['recommended_action']:<13}"
        )
        cli_ctx.log(
            f"{label} {item['component_name']}  [{item['condition']}]",
            "info",
        )
        if item.get("notes"):
            cli_ctx.log(f"              notes: {item['notes']}", "info")

    if output:
        from pathlib import Path

        Path(output).write_text(json.dumps(data, indent=2))
        cli_ctx.log(f"\nWritten to {output}", "info")


# ---------------------------------------------------------------------------
# salvage-match
# ---------------------------------------------------------------------------


@asset_group.command("salvage-match")
@click.option(
    "--component-name", default=None, help="Substring to match against component names"
)
@click.option("--part-number", default=None, help="Exact part number to match")
@click.option("--manifest-id", default=None, help="Scope search to this manifest UUID")
@click.option(
    "--condition",
    "conditions",
    multiple=True,
    type=click.Choice(["intact", "damaged", "missing", "unknown"]),
    help="Filter by observed condition (repeatable)",
)
@click.option("--output", "-o", default=None, help="Write results to a JSON file")
@async_command
@click.pass_context
async def salvage_match_cmd(
    ctx, component_name, part_number, manifest_id, conditions, output
):
    """Find harvestable components across the asset fleet.

    At least one of --component-name or --part-number is required.
    Name matching is case-insensitive substring; part number is exact.

    \b
    Examples:
      ohm asset salvage-match --component-name "Blood pump"
      ohm asset salvage-match --part-number BLOODPUMP-01
      ohm asset salvage-match --component-name pump --manifest-id <uuid>
      ohm asset salvage-match --component-name pump --condition damaged --condition intact
    """
    cli_ctx = ctx.obj

    if not component_name and not part_number:
        raise click.UsageError(
            "Provide at least one of --component-name or --part-number"
        )

    payload: Dict[str, Any] = {}
    if component_name:
        payload["component_name"] = component_name
    if part_number:
        payload["part_number"] = part_number
    if manifest_id:
        payload["manifest_id"] = manifest_id
    if conditions:
        payload["conditions"] = list(conditions)

    async def http_match():
        async with cli_ctx.api_client.get_client() as client:
            r = await client.post("/api/asset/salvage-match", json=payload)
            r.raise_for_status()
            return r.json()

    async def fallback_match():
        svc = await AssetService.get_instance()
        result = await svc.salvage_match(
            component_name=component_name,
            part_number=part_number,
            manifest_id=manifest_id,
            conditions=list(conditions) if conditions else None,
        )
        return result.to_dict()

    command = SmartCommand(cli_ctx)
    data = await command.execute_with_fallback(http_match, fallback_match)

    total = data.get("total", len(data.get("matches", [])))
    cli_ctx.log(f"{total} match(es) found.", "success")
    for m in data.get("matches", []):
        flags = []
        if m.get("salvageable"):
            flags.append("salvageable")
        if m.get("replaceable"):
            flags.append("replaceable")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        loc = f"  @ {m['location']}" if m.get("location") else ""
        cli_ctx.log(
            f"  {m['component_name']}  [{m['condition']}]{flag_str}",
            "info",
        )
        cli_ctx.log(
            f"    asset={m['asset_id'][:8]}…  tag={m['asset_tag']}{loc}",
            "info",
        )
        if m.get("part_number"):
            cli_ctx.log(f"    pn={m['part_number']}", "info")
        if m.get("notes"):
            cli_ctx.log(f"    notes: {m['notes']}", "info")

    if output:
        Path(output).write_text(json.dumps(data, indent=2))
        cli_ctx.log(f"Written to {output}", "info")


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
