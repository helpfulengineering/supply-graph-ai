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


@identity_group.group(name="identities")
def identities_group() -> None:
    """Mint, show, and rotate self-sovereign identities (did:key)."""
    pass


@identities_group.command(name="create")
@standard_cli_command(help_text="Mint an identity for an account.", async_cmd=True)
@click.option("--account-id", required=True, help="Owning account id")
@click.option(
    "--kind", type=click.Choice(["person", "space"]), default="person", help="Kind"
)
@click.option("--name", "display_name", default="", help="Display name")
@click.pass_context
async def identities_create(
    ctx: click.Context,
    account_id: str,
    kind: str,
    display_name: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Mint an Ed25519 did:key bound to an account."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    payload = {"account_id": account_id, "kind": kind, "display_name": display_name}
    try:
        result = await _request(cli_ctx, "POST", "/identities", json=payload)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Minted identity {result.get('did')}", "success")


@identities_group.command(name="show")
@standard_cli_command(help_text="Show an identity by DID.", async_cmd=True)
@click.argument("did")
@click.pass_context
async def identities_show(
    ctx: click.Context,
    did: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Show a held identity record."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", f"/identities/{did}")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"DID: {result.get('did')}", "info")
    cli_ctx.log(
        f"Kind: {result.get('kind')}  Account: {result.get('account_id')}", "info"
    )
    cli_ctx.log(f"Links: {len(result.get('links_in', []))}", "success")


@identities_group.command(name="rotate")
@standard_cli_command(help_text="Rotate an identity's key.", async_cmd=True)
@click.argument("did")
@click.pass_context
async def identities_rotate(
    ctx: click.Context,
    did: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Rotate to a fresh keypair, linking old -> new."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "POST", f"/identities/{did}/rotate")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Rotated {did} -> {result.get('did')}", "success")


@identity_group.group(name="grants")
def grants_group() -> None:
    """Issue, list, and revoke capability grants."""
    pass


@grants_group.command(name="issue")
@standard_cli_command(help_text="Issue a capability grant.", async_cmd=True)
@click.option("--subject-did", required=True, help="DID the grant is for")
@click.option(
    "--permission",
    "permissions",
    multiple=True,
    default=("read",),
    help="Permission to grant (repeatable)",
)
@click.option("--scope-kind", default="node", help="Scope kind: node|space|pool|record")
@click.option("--scope-target", required=True, help="Scope target (DID / pool / hash)")
@click.option("--issuer-did", default=None, help="Issuer DID (defaults to node)")
@click.option("--ttl-days", type=int, default=None, help="Lifetime in days")
@click.option(
    "--floor",
    "coarse_floor",
    multiple=True,
    help="Coarse floor permission (repeatable): read|write|admin|domain:x",
)
@click.pass_context
async def grants_issue(
    ctx: click.Context,
    subject_did: str,
    permissions: tuple,
    scope_kind: str,
    scope_target: str,
    issuer_did: Optional[str],
    ttl_days: Optional[int],
    coarse_floor: tuple,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Issue a signed capability grant."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    payload: dict = {
        "subject_did": subject_did,
        "permissions": list(permissions),
        "scope": {"kind": scope_kind, "target": scope_target},
    }
    if issuer_did:
        payload["issuer_did"] = issuer_did
    if ttl_days is not None:
        payload["ttl_days"] = ttl_days
    if coarse_floor:
        payload["coarse_floor"] = list(coarse_floor)
    try:
        result = await _request(cli_ctx, "POST", "/grants", json=payload)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Issued grant {result.get('grant_id')}", "success")
    cli_ctx.log(f"  expires: {result.get('expires_at')}", "info")


@grants_group.command(name="list")
@standard_cli_command(help_text="List grants for a subject DID.", async_cmd=True)
@click.option("--subject-did", required=True, help="Subject DID to list grants for")
@click.pass_context
async def grants_list(
    ctx: click.Context,
    subject_did: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List capability grants held for a subject."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", f"/grants?subject_did={subject_did}")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Grants ({len(result)})", "success")
    for grant in result:
        scope = grant.get("scope", {})
        perms = ", ".join(grant.get("permissions", []))
        click.echo(
            f"  {grant.get('grant_id')}  {scope.get('kind')}:{scope.get('target')}"
            f"  [{perms}]  exp {grant.get('expires_at')}"
        )


@grants_group.command(name="revoke")
@standard_cli_command(help_text="Revoke a grant by id.", async_cmd=True)
@click.argument("grant_id")
@click.pass_context
async def grants_revoke(
    ctx: click.Context,
    grant_id: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Revoke a capability grant."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "DELETE", f"/grants/{grant_id}")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Revoked grant {grant_id}", "success")


@grants_group.command(name="bootstrap-edge")
@standard_cli_command(
    help_text="Self-issue a genesis grant on the local node (edge bootstrap).",
    async_cmd=True,
)
@click.option("--subject-did", required=True, help="Subject DID (signs its own grant)")
@click.pass_context
async def grants_bootstrap_edge(
    ctx: click.Context,
    subject_did: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Isolated-edge bootstrap: subject self-issues write on the local node."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(
            cli_ctx,
            "POST",
            f"/grants/bootstrap-edge?subject_did={subject_did}",
        )
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Bootstrapped edge grant {result.get('grant_id')}", "success")


@identity_group.group(name="spaces")
def spaces_group() -> None:
    """Claim and inspect space admin bindings (TOFU)."""
    pass


@spaces_group.command(name="claim")
@standard_cli_command(
    help_text="TOFU-claim a SPACE identity for a PERSON admin.", async_cmd=True
)
@click.option("--space-did", required=True, help="Space DID to claim")
@click.option("--admin-did", required=True, help="Person DID who will administer it")
@click.pass_context
async def spaces_claim(
    ctx: click.Context,
    space_did: str,
    admin_did: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Bind a person as admin of a space (first claimer wins)."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(
            cli_ctx,
            "POST",
            "/spaces/claim",
            json={"space_did": space_did, "admin_did": admin_did},
        )
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Claimed {space_did} for admin {admin_did}", "success")


@spaces_group.command(name="show")
@standard_cli_command(help_text="Show the claim for a space DID.", async_cmd=True)
@click.argument("space_did")
@click.pass_context
async def spaces_show(
    ctx: click.Context,
    space_did: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Show who administers a space."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", f"/spaces/{space_did}/claim")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(
        f"Space {result.get('space_did')} admin={result.get('admin_did')}", "info"
    )


@spaces_group.command(name="list")
@standard_cli_command(help_text="List space claims on this node.", async_cmd=True)
@click.pass_context
async def spaces_list(
    ctx: click.Context,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List all space claims."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", "/spaces")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Space claims ({len(result)})", "success")
    for claim in result:
        click.echo(f"  {claim.get('space_did')}  admin={claim.get('admin_did')}")


@identity_group.group(name="attestations")
def attestations_group() -> None:
    """Issue and inspect durable attestations (certification / reputation)."""
    pass


@attestations_group.command(name="issue")
@standard_cli_command(help_text="Issue a signed attestation.", async_cmd=True)
@click.option("--type", "att_type", required=True, help="Attestation type")
@click.option("--subject-did", required=True, help="Subject DID the claim is about")
@click.option("--issuer-did", default=None, help="Issuer DID (default: local node)")
@click.option("--content-hash", default=None, help="Optional content / bundle hash")
@click.pass_context
async def attestations_issue(
    ctx: click.Context,
    att_type: str,
    subject_did: str,
    issuer_did: Optional[str],
    content_hash: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Issue a durable signed attestation."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    body: dict = {"type": att_type, "subject_did": subject_did}
    if issuer_did:
        body["issuer_did"] = issuer_did
    if content_hash:
        body["content_hash"] = content_hash
    try:
        result = await _request(cli_ctx, "POST", "/attestations", json=body)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(
        f"Issued {result.get('type')} attestation {result.get('attestation_id')}",
        "success",
    )


@attestations_group.command(name="certify")
@standard_cli_command(
    help_text="Certify a release (firm DID → bundle hash → version).", async_cmd=True
)
@click.option(
    "--subject-did", required=True, help="Firm / space DID standing behind it"
)
@click.option("--bundle-hash", required=True, help="R3 bundle hash (sha256:...)")
@click.option("--version", required=True, help="Release version string")
@click.option("--issuer-did", default=None, help="Issuer DID (default: local node)")
@click.option(
    "--manifest-content-hash",
    default=None,
    help="Design content hash (so the attestation rides federation catalog)",
)
@click.pass_context
async def attestations_certify(
    ctx: click.Context,
    subject_did: str,
    bundle_hash: str,
    version: str,
    issuer_did: Optional[str],
    manifest_content_hash: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Issue a certified attestation over a pin-record bundle hash."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    body: dict = {
        "subject_did": subject_did,
        "bundle_hash": bundle_hash,
        "version": version,
    }
    if issuer_did:
        body["issuer_did"] = issuer_did
    if manifest_content_hash:
        body["manifest_content_hash"] = manifest_content_hash
    try:
        result = await _request(cli_ctx, "POST", "/attestations/certify", json=body)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(
        f"Certified {bundle_hash} as {version} for {subject_did} "
        f"({result.get('attestation_id')})",
        "success",
    )


@attestations_group.command(name="list")
@standard_cli_command(help_text="List attestations.", async_cmd=True)
@click.option("--subject-did", default=None, help="Filter by subject DID")
@click.option("--content-hash", default=None, help="Filter by content / bundle hash")
@click.pass_context
async def attestations_list(
    ctx: click.Context,
    subject_did: Optional[str],
    content_hash: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List attestations, optionally filtered."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    params = []
    if subject_did:
        params.append(f"subject_did={subject_did}")
    if content_hash:
        params.append(f"content_hash={content_hash}")
    path = "/attestations" + (f"?{'&'.join(params)}" if params else "")
    try:
        result = await _request(cli_ctx, "GET", path)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Attestations ({len(result)})", "success")
    for att in result:
        click.echo(
            f"  {att.get('type')}  subject={att.get('subject_did')}  "
            f"hash={att.get('content_hash')}"
        )


@identity_group.command(name="reputation")
@standard_cli_command(
    help_text="Show known-type attestations about a subject (reputation).",
    async_cmd=True,
)
@click.argument("subject_did")
@click.pass_context
async def reputation(
    ctx: click.Context,
    subject_did: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List signature-valid known-type attestations about a subject."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", f"/reputation/{subject_did}")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Reputation for {subject_did} ({len(result)})", "success")
    for att in result:
        click.echo(
            f"  {att.get('type')}  by={att.get('issuer_did')}  "
            f"hash={att.get('content_hash')}"
        )


@identity_group.group(name="bindings")
def bindings_group() -> None:
    """Optional domain / OAuth bindings (online convenience layer)."""
    pass


@bindings_group.command(name="domain-start")
@standard_cli_command(
    help_text="Start a domain binding; print the .well-known document to host.",
    async_cmd=True,
)
@click.option("--subject-did", required=True, help="DID to bind")
@click.option("--domain", required=True, help="Domain host (e.g. example.org)")
@click.pass_context
async def bindings_domain_start(
    ctx: click.Context,
    subject_did: str,
    domain: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Issue a domain-bind challenge and well-known document."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(
            cli_ctx,
            "POST",
            "/bindings/domain",
            json={"subject_did": subject_did, "domain": domain},
        )
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Host this at {result.get('well_known_url')}", "success")
    click.echo(format_llm_output(result.get("well_known_document"), cli_ctx))


@bindings_group.command(name="domain-verify")
@standard_cli_command(
    help_text="Verify a domain binding by fetching .well-known/ohm-did.json.",
    async_cmd=True,
)
@click.option("--subject-did", required=True, help="DID that started the bind")
@click.option("--domain", required=True, help="Domain host")
@click.pass_context
async def bindings_domain_verify(
    ctx: click.Context,
    subject_did: str,
    domain: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Fetch and validate the well-known document, then mark verified."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(
            cli_ctx,
            "POST",
            "/bindings/domain/verify",
            json={"subject_did": subject_did, "domain": domain},
        )
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(
        f"Verified {result.get('external_id')} for {result.get('subject_did')}",
        "success",
    )


@bindings_group.command(name="oauth")
@standard_cli_command(
    help_text="Record an OAuth/OIDC binding (after IdP verification).",
    async_cmd=True,
)
@click.option("--subject-did", required=True, help="DID to bind")
@click.option("--provider", required=True, help="IdP name (github, google, orcid, …)")
@click.option("--external-subject", required=True, help="IdP subject / username")
@click.pass_context
async def bindings_oauth(
    ctx: click.Context,
    subject_did: str,
    provider: str,
    external_subject: str,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Persist an external IdP subject binding."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(
            cli_ctx,
            "POST",
            "/bindings/oauth",
            json={
                "subject_did": subject_did,
                "provider": provider,
                "external_subject": external_subject,
            },
        )
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(
        f"Bound {result.get('external_id')} to {result.get('subject_did')}",
        "success",
    )


@bindings_group.command(name="list")
@standard_cli_command(help_text="List identity bindings.", async_cmd=True)
@click.option("--subject-did", default=None, help="Filter by subject DID")
@click.pass_context
async def bindings_list(
    ctx: click.Context,
    subject_did: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List domain/OAuth bindings."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    path = "/bindings" + (f"?subject_did={subject_did}" if subject_did else "")
    try:
        result = await _request(cli_ctx, "GET", path)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Bindings ({len(result)})", "success")
    for b in result:
        flag = "verified" if b.get("verified") else "pending"
        click.echo(
            f"  {b.get('kind')}  {b.get('external_id')}  "
            f"subject={b.get('subject_did')}  [{flag}]"
        )


@identity_group.group(name="directory")
def directory_group() -> None:
    """Trust-on-follow directory (peacetime registry posture)."""
    pass


@directory_group.command(name="publish")
@standard_cli_command(
    help_text="Publish or refresh a directory entry for a DID.", async_cmd=True
)
@click.option("--did", required=True, help="DID to publish")
@click.option("--name", "display_name", default="", help="Display name")
@click.option("--base-url", default=None, help="Federation base URL")
@click.option("--domain", default=None, help="Bound domain (optional)")
@click.pass_context
async def directory_publish(
    ctx: click.Context,
    did: str,
    display_name: str,
    base_url: Optional[str],
    domain: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """Publish a trust-on-follow directory entry."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    body: dict = {"did": did, "display_name": display_name}
    if base_url:
        body["base_url"] = base_url
    if domain:
        body["domain"] = domain
    try:
        result = await _request(cli_ctx, "POST", "/directory", json=body)
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Published directory entry for {did}", "success")


@directory_group.command(name="list")
@standard_cli_command(help_text="List the trust-on-follow directory.", async_cmd=True)
@click.pass_context
async def directory_list(
    ctx: click.Context,
    verbose: bool,
    output_format: str,
    use_llm: bool,
    llm_provider: str,
    llm_model: Optional[str],
    quality_level: str,
    strict_mode: bool,
) -> None:
    """List known DIDs in the local directory."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.verbose = verbose
    try:
        result = await _request(cli_ctx, "GET", "/directory")
    except httpx.HTTPStatusError as e:
        if _handle_auth_error(cli_ctx, e):
            return
        raise

    if output_format == "json":
        click.echo(format_llm_output(result, cli_ctx))
        return
    cli_ctx.log(f"Directory ({len(result)})", "success")
    for entry in result:
        click.echo(
            f"  {entry.get('did')}  name={entry.get('display_name')}  "
            f"domain={entry.get('domain')}  "
            f"bindings={len(entry.get('verified_bindings') or [])}"
        )
