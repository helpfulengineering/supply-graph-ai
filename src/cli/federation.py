"""Federation LAN peer discovery and status commands."""

from __future__ import annotations

from typing import Optional

import click
import httpx

from .base import CLIContext, format_llm_output
from .decorators import standard_cli_command

_FEDERATION_PREFIX = "/v1/api/federation"


@click.group()
def federation_group() -> None:
    """
    Federation peer discovery and node status.

    Examples:
      ohm federation status
      ohm federation peers --discover
      ohm federation follow did:key:z6Mk...
      ohm federation sync --peer http://peer-b:8001
    """
    pass


def _federation_url(cli_ctx: CLIContext, path: str) -> str:
    base = cli_ctx.config.server_url.rstrip("/")
    return f"{base}{_FEDERATION_PREFIX}{path}"


async def _get_json(cli_ctx: CLIContext, path: str) -> dict:
    url = _federation_url(cli_ctx, path)
    async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def _post_json(
    cli_ctx: CLIContext,
    path: str,
    json: dict | None = None,
    params: dict | None = None,
) -> dict:
    url = _federation_url(cli_ctx, path)
    async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
        response = await client.post(url, json=json, params=params)
        response.raise_for_status()
        return response.json()


@federation_group.command()
@standard_cli_command(
    help_text="Show federation node identity and catalog summary.",
    async_cmd=True,
    handle_errors=True,
)
@click.pass_context
async def status(
    ctx: click.Context,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Display this node's federation identity."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose

    try:
        identify = await _get_json(cli_ctx, "/identify")
        health = await _get_json(cli_ctx, "/health")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            cli_ctx.log(
                "Federation is not enabled on the server "
                "(set OHM_FEDERATION_ENABLED=true)",
                "error",
            )
            return
        raise

    payload = {"identify": identify, "health": health}
    if output_format == "json":
        click.echo(format_llm_output(payload, cli_ctx))
        return

    cli_ctx.log(f"DID: {identify.get('did')}", "info")
    cli_ctx.log(f"Name: {identify.get('display_name')}", "info")
    cli_ctx.log(f"Role: {identify.get('role')}", "info")
    cli_ctx.log(f"Catalog records: {identify.get('catalog_record_count', 0)}", "info")
    cli_ctx.log(f"Merkle root: {identify.get('merkle_root')}", "info")
    cli_ctx.log(f"Health: {health.get('status')}", "success")


@federation_group.command()
@standard_cli_command(
    help_text="List known federation peers; use --discover to refresh from LAN.",
    async_cmd=True,
    handle_errors=True,
)
@click.option(
    "--discover",
    is_flag=True,
    help="Run peer discovery (manual peers + mDNS) before listing",
)
@click.pass_context
async def peers(
    ctx: click.Context,
    discover: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List or discover federation peers."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose

    try:
        if discover:
            result = await _post_json(cli_ctx, "/peers/discover")
            peer_list = result.get("peers", [])
            updated = result.get("updated", [])
            if cli_ctx.verbose:
                cli_ctx.log(f"Updated {len(updated)} peer(s) this run", "info")
        else:
            result = await _get_json(cli_ctx, "/peers")
            peer_list = result.get("peers", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            cli_ctx.log(
                "Federation is not enabled on the server "
                "(set OHM_FEDERATION_ENABLED=true)",
                "error",
            )
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return

    if not peer_list:
        cli_ctx.log("No peers known yet (try: ohm federation peers --discover)", "info")
        return

    cli_ctx.log(f"Peers ({len(peer_list)})", "success")
    for peer in peer_list:
        name = peer.get("display_name") or peer.get("did", "?")[:20]
        source = peer.get("source", "?")
        url = peer.get("base_url", "")
        followed = "followed" if peer.get("followed") else "not followed"
        click.echo(f"  {name} [{source}] {url} ({followed})")


@federation_group.command()
@standard_cli_command(
    help_text="Follow or unfollow a peer DID for manifest sync.",
    async_cmd=True,
    handle_errors=True,
)
@click.argument("did")
@click.option("--unfollow", is_flag=True, help="Remove from follow allowlist")
@click.pass_context
async def follow(
    ctx: click.Context,
    did: str,
    unfollow: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Follow or unfollow a federation peer by DID."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose

    path = f"/peers/{did}/follow"
    try:
        if unfollow:
            url = _federation_url(cli_ctx, path)
            async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
                response = await client.delete(url)
                response.raise_for_status()
                result = response.json()
        else:
            result = await _post_json(cli_ctx, path)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            cli_ctx.log("Federation is not enabled on the server", "error")
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return

    action = "Unfollowed" if unfollow else "Followed"
    cli_ctx.log(f"{action} {did}", "success")


@federation_group.command()
@standard_cli_command(
    help_text="Run anti-entropy sync with followed peers or one peer URL.",
    async_cmd=True,
    handle_errors=True,
)
@click.option("--peer", "peer_url", help="Sync a single peer base URL")
@click.pass_context
async def sync(
    ctx: click.Context,
    peer_url: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Pull missing manifests from followed peers."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose

    path = "/sync/run"
    params = {"peer_url": peer_url} if peer_url else None

    try:
        result = await _post_json(cli_ctx, path, params=params)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            cli_ctx.log("Federation is not enabled on the server", "error")
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return

    total = result.get("total_pulled", 0)
    cli_ctx.log(f"Sync complete: {total} record(s) pulled", "success")
    for peer_result in result.get("results", []):
        name = peer_result.get("peer_did", "?")[:24]
        pulled = peer_result.get("pulled", 0)
        errors = peer_result.get("errors", [])
        click.echo(f"  {name}: pulled={pulled}")
        for err in errors:
            click.echo(f"    error: {err}")
