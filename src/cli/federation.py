"""Federation LAN peer discovery and status commands."""

from __future__ import annotations

import os
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


def _list_entries(pins: tuple[str, ...], replaces: tuple[str, ...]) -> list[dict]:
    replaced: dict[str, str] = {}
    for item in replaces:
        new, _, old = item.partition("=")
        replaced[new] = old
    entries = []
    for pin in pins:
        entry = {"content_hash": pin}
        if pin in replaced:
            entry["supersedes"] = replaced[pin]
        entries.append(entry)
    return entries


async def _send(
    cli_ctx: CLIContext, method: str, path: str, json: dict | None = None
) -> dict:
    token = os.getenv("OHM_API_KEY")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
        response = await client.request(
            method, _federation_url(cli_ctx, path), json=json, headers=headers
        )
        response.raise_for_status()
        return response.json()


def _print_list(cli_ctx: CLIContext, document: dict, output_format: str) -> None:
    if output_format == "json":
        click.echo(format_llm_output(document, cli_ctx))
        return
    cli_ctx.log(
        f"{document.get('name')} (sequence {document.get('sequence')})", "success"
    )
    cli_ctx.log(f"Publisher: {document.get('publisher_did')}", "info")
    for entry in document.get("entries") or []:
        line = entry.get("content_hash", "")
        if entry.get("supersedes"):
            line = f"{line} replaces {entry['supersedes']}"
        click.echo(f"  {line}")


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


@federation_group.command("okw-sync")
@standard_cli_command(
    help_text="Sync OKW catalog (redacted facilities) from followed peers.",
    async_cmd=True,
    handle_errors=True,
)
@click.pass_context
async def okw_sync(
    ctx: click.Context,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Pull missing OKW catalog records from followed peers."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _post_json(cli_ctx, "/okw/sync/run")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            cli_ctx.log("Federation is not enabled on the server", "error")
            return
        raise
    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    total = result.get("total_pulled", 0)
    cli_ctx.log(f"OKW sync complete: {total} record(s) pulled", "success")


@federation_group.command("package-fetch")
@standard_cli_command(
    help_text="On-demand fetch of a package artifact from a peer (CAS channel).",
    async_cmd=True,
    handle_errors=True,
)
@click.option("--peer", "peer_url", required=True, help="Peer base URL")
@click.option("--bundle-hash", required=True, help="Package bundle_hash (sha256:…)")
@click.option("--manifest-id", default=None, help="OKH id for rebuild fallback")
@click.option(
    "--no-rebuild",
    is_flag=True,
    help="Do not rebuild from OKH URLs if fetch fails",
)
@click.pass_context
async def package_fetch(
    ctx: click.Context,
    peer_url: str,
    bundle_hash: str,
    manifest_id: Optional[str],
    no_rebuild: bool,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Pull package bytes from a followed peer; rebuild from OKH if needed."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose

    body = {
        "peer_url": peer_url,
        "bundle_hash": bundle_hash,
        "allow_rebuild": not no_rebuild,
    }
    if manifest_id:
        body["manifest_id"] = manifest_id

    try:
        result = await _post_json(cli_ctx, "/packages/fetch", json=body)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            cli_ctx.log("Federation is not enabled on the server", "error")
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return

    action = result.get("action", "?")
    path = result.get("path") or ""
    detail = result.get("detail") or ""
    if action in ("fetched", "rebuilt", "local"):
        cli_ctx.log(f"Package {action}: {path}", "success")
        if detail:
            cli_ctx.log(detail, "info")
    else:
        cli_ctx.log(f"Package fetch failed: {detail}", "error")


@click.group()
def lists() -> None:
    """Publish a curated list of pinned designs.

    Examples:
      ohm federation lists publish --name "Field designs" --pin sha256:abc
      ohm federation lists update LIST_ID --name "Field designs" --pin sha256:def --replaces sha256:def=sha256:abc
    """


federation_group.add_command(lists)


def _list_command_options(func):
    func = click.option("--name", required=True, help="Display name of the list")(func)
    func = click.option(
        "--pin",
        "pins",
        multiple=True,
        required=True,
        help="Content hash to include. Repeat for each pin.",
    )(func)
    func = click.option(
        "--replaces",
        multiple=True,
        help="NEW=OLD. The new pin replaces OLD, which leaves the list.",
    )(func)
    return func


@lists.command("publish")
@click.option(
    "--publisher",
    default=None,
    help="Organisation DID. Omit to publish as this node. Signed by the space key.",
)
@_list_command_options
@standard_cli_command(
    help_text=(
        "Publish a named list of pinned content hashes. "
        "A private or members design is refused. "
        "Set OHM_API_KEY to an admin key, or to the organisation admin's key."
    ),
    async_cmd=True,
    handle_errors=True,
)
@click.pass_context
async def publish_list_cmd(
    ctx: click.Context,
    publisher: Optional[str],
    name: str,
    pins: tuple[str, ...],
    replaces: tuple[str, ...],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Create a curated list and sign its current membership."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    body: dict = {"name": name, "entries": _list_entries(pins, replaces)}
    if publisher:
        body["publisher_did"] = publisher
    document = await _send(cli_ctx, "POST", "/lists", json=body)
    _print_list(cli_ctx, document, output_format)


@lists.command("update")
@click.argument("list_id")
@_list_command_options
@standard_cli_command(
    help_text=(
        "Publish the next membership of a list. "
        "Sequence increases by one. "
        "A pin named in --replaces records the hash it replaces."
    ),
    async_cmd=True,
    handle_errors=True,
)
@click.pass_context
async def update_list_cmd(
    ctx: click.Context,
    list_id: str,
    name: str,
    pins: tuple[str, ...],
    replaces: tuple[str, ...],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Add, bump, or remove pins."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    document = await _send(
        cli_ctx,
        "PUT",
        f"/lists/{list_id}",
        json={"name": name, "entries": _list_entries(pins, replaces)},
    )
    _print_list(cli_ctx, document, output_format)


@lists.command("show")
@click.argument("list_id")
@standard_cli_command(
    help_text="Show a published list, including its signature.",
    async_cmd=True,
    handle_errors=True,
)
@click.pass_context
async def show_list_cmd(
    ctx: click.Context,
    list_id: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Fetch the signed document."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    document = await _send(cli_ctx, "GET", f"/lists/{list_id}")
    _print_list(cli_ctx, document, output_format)
