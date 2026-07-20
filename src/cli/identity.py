"""Identity CLI — manage API keys and accounts against the OHM server.

Backed by the ``/api/identity`` surface. When the server enforces write auth
(peacetime production), management calls need an admin key: set ``OHM_API_KEY``
and it is sent as ``Authorization: Bearer``.
"""

from __future__ import annotations

import os
from typing import Optional

import click
import httpx

from .base import CLIContext, format_llm_output
from .decorators import standard_cli_command

_IDENTITY_PREFIX = "/v1/api/identity"


@click.group()
def identity_group() -> None:
    """Manage API keys and accounts.

    Examples:
      ohm identity whoami
      ohm identity keys create --name ci --permission write
      ohm identity accounts create --name "MIT FabLab" --kind space
    """
    pass


def _url(cli_ctx: CLIContext, path: str) -> str:
    base = cli_ctx.config.server_url.rstrip("/")
    return f"{base}{_IDENTITY_PREFIX}{path}"


def _headers() -> dict:
    token = os.getenv("OHM_API_KEY")
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _request(
    cli_ctx: CLIContext,
    method: str,
    path: str,
    json: Optional[dict] = None,
) -> dict:
    async with httpx.AsyncClient(timeout=cli_ctx.config.timeout) as client:
        response = await client.request(
            method, _url(cli_ctx, path), json=json, headers=_headers()
        )
        response.raise_for_status()
        return response.json()


def _handle_auth_error(cli_ctx: CLIContext, exc: httpx.HTTPStatusError) -> bool:
    """Print a helpful hint for 401/403; return True if handled."""
    if exc.response.status_code in (401, 403):
        cli_ctx.log(
            "Not authorized. Set OHM_API_KEY to an admin key "
            "(the server enforces auth for this operation).",
            "error",
        )
        return True
    return False


@identity_group.command()
@standard_cli_command(help_text="Show the current identity.", async_cmd=True)
@click.pass_context
async def whoami(
    ctx: click.Context,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Display the account + permissions behind OHM_API_KEY."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", "/whoami")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Account: {result.get('account_id')}", "info")
    cli_ctx.log(f"Key: {result.get('name')}", "info")
    cli_ctx.log(f"Permissions: {', '.join(result.get('permissions', []))}", "success")


@identity_group.group(name="keys")
def keys_group() -> None:
    """Create, list, and revoke API keys."""
    pass


@keys_group.command(name="create")
@standard_cli_command(help_text="Mint a new API key.", async_cmd=True)
@click.option("--name", required=True, help="Human-readable key name")
@click.option(
    "--permission",
    "permissions",
    multiple=True,
    default=("read",),
    help="Permission to grant (repeatable): read|write|admin|domain:x",
)
@click.option("--account-id", help="Owning account id (defaults to root account)")
@click.pass_context
async def keys_create(
    ctx: click.Context,
    name: str,
    permissions: tuple,
    account_id: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Mint an API key; the token is shown only once."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    payload = {"name": name, "permissions": list(permissions)}
    if account_id:
        payload["account_id"] = account_id
    try:
        result = await _request(cli_ctx, "POST", "/keys", json=payload)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Created key {result.get('key_id')}", "success")
    cli_ctx.log(f"Token (store now, shown once): {result.get('token')}", "warning")


@keys_group.command(name="list")
@standard_cli_command(help_text="List API keys.", async_cmd=True)
@click.pass_context
async def keys_list(
    ctx: click.Context,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List API keys (tokens are never shown)."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", "/keys")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"API keys ({len(result)})", "success")
    for key in result:
        state = "revoked" if key.get("revoked") else "active"
        perms = ", ".join(key.get("permissions", []))
        click.echo(f"  {key.get('key_id')}  {key.get('name')}  [{state}]  {perms}")


@keys_group.command(name="revoke")
@standard_cli_command(help_text="Revoke an API key by id.", async_cmd=True)
@click.argument("key_id")
@click.pass_context
async def keys_revoke(
    ctx: click.Context,
    key_id: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Revoke an API key."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "DELETE", f"/keys/{key_id}")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Revoked key {key_id}", "success")


@identity_group.group(name="accounts")
def accounts_group() -> None:
    """Create, list, and disable accounts."""
    pass


@accounts_group.command(name="create")
@standard_cli_command(help_text="Create an account.", async_cmd=True)
@click.option("--name", "display_name", required=True, help="Display name")
@click.option(
    "--kind",
    type=click.Choice(["person", "space"]),
    default="person",
    help="Account kind",
)
@click.pass_context
async def accounts_create(
    ctx: click.Context,
    display_name: str,
    kind: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Create a person or space account."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    payload = {"display_name": display_name, "kind": kind}
    try:
        result = await _request(cli_ctx, "POST", "/accounts", json=payload)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Created account {result.get('id')} ({result.get('kind')})", "success")


@accounts_group.command(name="list")
@standard_cli_command(help_text="List accounts.", async_cmd=True)
@click.pass_context
async def accounts_list(
    ctx: click.Context,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List accounts."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", "/accounts")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Accounts ({len(result)})", "success")
    for acc in result:
        state = "disabled" if acc.get("disabled") else "active"
        click.echo(
            f"  {acc.get('id')}  {acc.get('display_name')}  "
            f"({acc.get('kind')})  [{state}]"
        )


@accounts_group.command(name="disable")
@standard_cli_command(help_text="Disable an account by id.", async_cmd=True)
@click.argument("account_id")
@click.pass_context
async def accounts_disable(
    ctx: click.Context,
    account_id: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Disable an account."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "POST", f"/accounts/{account_id}/disable")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Disabled account {account_id}", "success")
