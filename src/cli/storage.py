"""
Storage management commands for OHM CLI

This module provides commands for setting up and managing storage systems,
including directory structure creation and data population.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

import click

from ..config.storage_config import (
    StorageConfig,
    StorageConfigError,
    create_storage_config,
)
from ..core.services.storage_service import StorageService
from ..core.services.storage_setup import setup_storage
from ..core.storage.organizer import StorageOrganizer
from ..core.utils.logging import get_logger
from .decorators import standard_cli_command
from .progress import emit_status_line

logger = get_logger(__name__)


@click.group()
def storage_group() -> None:
    """
    Storage management commands for OHM.

    These commands help you set up and manage storage systems,
    including directory structure creation and data population.

    🏠 LOCAL STORAGE (Recommended for Getting Started)
    Local storage is the easiest way to get started - no credentials needed!
    Just specify a path on your local filesystem or network drive.

    ☁️ CLOUD STORAGE (For Production/Teams)
    Cloud storage providers (AWS S3, Azure Blob, Google Cloud) offer
    automatic backups, scalability, and team collaboration features.

    Examples:
      # Setup local storage (easiest!)
      ohm storage setup --provider local

      # Setup with custom local path
      ohm storage setup --provider local --bucket ~/ohm-data

      # Setup cloud storage (requires credentials in .env)
      ohm storage setup --provider gcs --bucket my-bucket --region us-central1

      # Populate storage with synthetic data
      ohm storage populate --provider local
    """
    pass


@storage_group.command()
@click.option(
    "--provider",
    type=click.Choice(["local", "gcs", "azure_blob", "aws_s3"]),
    default="local",
    help="Storage provider to use",
)
@click.option(
    "--storage-path",
    "--path",
    help="Local storage path (for local provider only). Overrides LOCAL_STORAGE_PATH and --bucket. "
    "Examples: ./storage, ~/ohm-data, /mnt/nas/ohm-storage",
)
@click.option(
    "--bucket",
    "bucket_name",
    help="Bucket/container name (required for cloud providers, or local directory name)",
)
@click.option("--region", help="Region/location for cloud providers")
@click.option("--credentials-json", help="Path to credentials JSON file (for GCP)")
@click.option("--project-id", help="GCP project ID (for GCS)")
@click.option("--account-name", help="Azure storage account name")
@click.option("--account-key", help="Azure storage account key")
@click.option("--access-key", help="AWS access key ID")
@click.option("--secret-key", help="AWS secret access key")
@standard_cli_command(
    help_text="""
    Set up the directory structure in a storage system.
    
    This command creates the organized directory structure needed
    for storing OKH manifests, OKW facilities, and supply trees.
    
    The directory structure includes:
    - okh/manifests/ - For OKH manifest files
    - okw/facilities/ - For OKW facility files (manufacturing, makerspaces, research)
    - supply-trees/ - For supply tree solutions (generated, validated)
    
    🏠 LOCAL STORAGE (Default & Recommended)
    Local storage is the easiest option - no credentials required!
    - Works immediately after installation
    - Perfect for development, testing, and self-hosting
    - Supports local drives, home directories, and network storage
    
    ☁️ CLOUD STORAGE
    For cloud providers, you can provide credentials via:
    - Environment variables in .env file (recommended)
    - Command-line options (for testing)
    - Credentials files (for GCP)
    """,
    epilog="""
    Examples:
      # Setup local storage (easiest - default location: ./storage)
      ohm storage setup --provider local
      
      # Setup local storage with custom path (using --storage-path shortcut)
      ohm storage setup --provider local --storage-path ~/my-ohm-data
      
      # Setup local storage on network drive
      ohm storage setup --provider local --path /mnt/nas/ohm-storage
      
      # Alternative: Use --bucket for local storage (backward compatible)
      ohm storage setup --provider local --bucket ~/my-ohm-data
      
      # Setup GCS storage (requires GCP credentials in .env)
      ohm storage setup --provider gcs --bucket my-bucket --region us-central1
      
      # Setup Azure storage (requires Azure credentials in .env)
      ohm storage setup --provider azure_blob --bucket my-container
      
      # Setup AWS S3 storage (requires AWS credentials in .env)
      ohm storage setup --provider aws_s3 --bucket my-bucket --region us-east-1
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,
)
@click.pass_context
async def setup(
    ctx,
    provider: str,
    storage_path: Optional[str],
    bucket_name: Optional[str],
    region: Optional[str],
    credentials_json: Optional[str],
    project_id: Optional[str],
    account_name: Optional[str],
    account_key: Optional[str],
    access_key: Optional[str],
    secret_key: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Set up the directory structure in a storage system."""
    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose

    cli_ctx.start_command_tracking("storage-setup")

    try:
        emit_status_line(
            output_format=output_format,
            step="Preparing storage configuration",
            index=1,
            total=3,
        )
        # For local provider, --storage-path takes precedence over --bucket
        if provider == "local" and storage_path:
            bucket_name = storage_path
            cli_ctx.log(f"Using local storage path: {storage_path}", "info")

        # Build credentials dict based on provider
        credentials: Dict[str, str] = {}

        if provider == "gcs":
            if credentials_json:
                if os.path.exists(credentials_json):
                    credentials["credentials_path"] = credentials_json
                else:
                    credentials["credentials_json"] = credentials_json
            if project_id:
                credentials["project_id"] = project_id
        elif provider == "azure_blob":
            if account_name:
                credentials["account_name"] = account_name
            if account_key:
                credentials["account_key"] = account_key
        elif provider == "aws_s3":
            if access_key:
                credentials["access_key"] = access_key
            if secret_key:
                credentials["secret_key"] = secret_key
            if region:
                credentials["region"] = region

        # Create storage config
        if credentials:
            storage_config = StorageConfig(
                provider=provider,
                bucket_name=bucket_name or "storage",
                region=region,
                credentials=credentials,
            )
        else:
            storage_config = create_storage_config(provider, bucket_name, region)

        cli_ctx.log(f"Setting up storage structure for {provider}...", "info")

        # Display storage location prominently
        if provider == "local":
            # Get absolute path for display
            from pathlib import Path

            abs_path = Path(storage_config.bucket_name).resolve()
            cli_ctx.log(f"📁 Using local storage at: {abs_path}", "info")
        else:
            cli_ctx.log(f"Bucket: {storage_config.bucket_name}", "info")
            if region:
                cli_ctx.log(f"Region: {region}", "info")

        # Initialize storage service
        emit_status_line(
            output_format=output_format,
            step="Initializing storage service",
            index=2,
            total=3,
        )
        # Connect, prove the connection with a real round trip, then establish
        # the prefixes — all in the shared setup function (#372). This used to
        # go through StorageService.configure, which swallows connection
        # failures so the API can boot degraded; setup inherited that and
        # reported success on a backend it had never reached.
        emit_status_line(
            output_format=output_format,
            step="Creating storage directory structure",
            index=3,
            total=3,
        )
        result = await setup_storage(storage_config)

        if output_format == "json":
            output_data = {
                "status": "success",
                "region": region,
                # Kept under their old names: existing callers of
                # `--format json` read these two.
                "directories_created": len(result.prefixes_created),
                "directories": result.prefixes_created,
                **result.to_dict(),
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            # `log(..., "success")` adds its own ✅; the old line here carried a
            # second one and printed "✅ ✅".
            cli_ctx.log("Storage is ready.", "success")
            cli_ctx.log(f"Provider: {provider}", "info")

            if provider == "local":
                cli_ctx.log(f"Location: {result.location}", "info")
            else:
                cli_ctx.log(f"Bucket: {result.bucket}", "info")
                if region:
                    cli_ctx.log(f"Region: {region}", "info")

            if result.prefixes_created:
                cli_ctx.log(f"Created {len(result.prefixes_created)} prefixes:", "info")
                for prefix in result.prefixes_created:
                    click.echo(f"  - {prefix}")
            if result.prefixes_found:
                cli_ctx.log(f"Already present ({len(result.prefixes_found)}):", "info")
                for prefix in result.prefixes_found:
                    click.echo(f"  - {prefix}")
            if not result.initialized:
                cli_ctx.log("Nothing to do — storage was already set up.", "info")

        cli_ctx.end_command_tracking()

    except StorageConfigError as e:
        cli_ctx.log(f"❌ Configuration error: {e}", "error")
        raise
    except Exception as e:
        cli_ctx.log(f"❌ Failed to setup storage structure: {e}", "error")
        raise


@storage_group.command()
@click.option(
    "--provider",
    type=click.Choice(["local", "gcs", "azure_blob", "aws_s3"]),
    default="local",
    help="Storage provider to use",
)
@click.option(
    "--storage-path",
    "--path",
    help="Local storage path (for local provider only). Overrides LOCAL_STORAGE_PATH and --bucket. "
    "Examples: ./storage, ~/ohm-data, /mnt/nas/ohm-storage",
)
@click.option(
    "--bucket",
    "bucket_name",
    help="Bucket/container name (required for cloud providers, or local directory name)",
)
@click.option("--region", help="Region/location for cloud providers")
@click.option(
    "--data-dir",
    help="Path to synthetic data directory (defaults to synth/synthetic-data/)",
)
@click.option("--credentials-json", help="Path to credentials JSON file (for GCP)")
@click.option("--project-id", help="GCP project ID (for GCS)")
@click.option("--account-name", help="Azure storage account name")
@click.option("--account-key", help="Azure storage account key")
@click.option("--access-key", help="AWS access key ID")
@click.option("--secret-key", help="AWS secret access key")
@standard_cli_command(
    help_text="""
    Populate storage with synthetic data from synth/synthetic-data/.
    
    This command loads OKH and OKW files from the synthetic data directory
    and stores them in the configured storage system using the organized
    directory structure.
    
    The command will:
    - Load all *okh*.json files as OKH manifests
    - Load all *okw*.json files as OKW facilities
    - Store them in the appropriate directories with proper metadata
    
    This is useful for:
    - Testing your storage setup
    - Learning how OHM organizes data
    - Development and demonstrations
    """,
    epilog="""
    Examples:
      # Populate local storage (default)
      ohm storage populate --provider local
      
      # Populate local storage with custom path (using --storage-path shortcut)
      ohm storage populate --provider local --storage-path ~/my-ohm-data
      
      # Populate with custom data directory
      ohm storage populate --provider local --data-dir /path/to/data
      
      # Alternative: Use --bucket for local storage (backward compatible)
      ohm storage populate --provider local --bucket ~/my-ohm-data
      
      # Populate cloud storage (requires credentials in .env)
      ohm storage populate --provider gcs --bucket my-bucket
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,
)
@click.pass_context
async def populate(
    ctx,
    provider: str,
    storage_path: Optional[str],
    bucket_name: Optional[str],
    region: Optional[str],
    data_dir: Optional[str],
    credentials_json: Optional[str],
    project_id: Optional[str],
    account_name: Optional[str],
    account_key: Optional[str],
    access_key: Optional[str],
    secret_key: Optional[str],
    verbose: bool,
    output_format: str,
    use_llm: bool = False,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    quality_level: str = "professional",
    strict_mode: bool = False,
):
    """Populate storage with synthetic data."""
    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose

    cli_ctx.start_command_tracking("storage-populate")

    storage_service = None
    try:
        emit_status_line(
            output_format=output_format,
            step="Preparing storage configuration",
            index=1,
            total=4,
        )
        # For local provider, --storage-path takes precedence over --bucket
        if provider == "local" and storage_path:
            bucket_name = storage_path
            cli_ctx.log(f"Using local storage path: {storage_path}", "info")

        # Build credentials dict based on provider
        credentials: Dict[str, str] = {}

        if provider == "gcs":
            if credentials_json:
                if os.path.exists(credentials_json):
                    credentials["credentials_path"] = credentials_json
                else:
                    credentials["credentials_json"] = credentials_json
            if project_id:
                credentials["project_id"] = project_id
        elif provider == "azure_blob":
            if account_name:
                credentials["account_name"] = account_name
            if account_key:
                credentials["account_key"] = account_key
        elif provider == "aws_s3":
            if access_key:
                credentials["access_key"] = access_key
            if secret_key:
                credentials["secret_key"] = secret_key
            if region:
                credentials["region"] = region

        # Create storage config
        if credentials:
            storage_config = StorageConfig(
                provider=provider,
                bucket_name=bucket_name or "storage",
                region=region,
                credentials=credentials,
            )
        else:
            storage_config = create_storage_config(provider, bucket_name, region)

        # Determine data directory
        if data_dir is None:
            # Default to synth/synthetic-data/ relative to project root
            # __file__ is src/cli/storage.py, so:
            # parent = src/cli/
            # parent.parent = src/
            # parent.parent.parent = project root (supply-graph-ai/)
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "synth" / "synthetic-data"
        else:
            data_dir = Path(data_dir)

        if not data_dir.exists():
            raise FileNotFoundError(f"Synthetic data directory not found: {data_dir}")

        cli_ctx.log(
            f"Populating storage with synthetic data from {data_dir}...", "info"
        )
        cli_ctx.log(f"Provider: {provider}", "info")

        # Display storage location prominently
        if provider == "local":
            # Get absolute path for display
            abs_path = Path(storage_config.bucket_name).resolve()
            cli_ctx.log(f"📁 Target location: {abs_path}", "info")
        else:
            cli_ctx.log(f"Bucket: {storage_config.bucket_name}", "info")

        # Initialize storage service
        emit_status_line(
            output_format=output_format,
            step="Initializing storage service",
            index=2,
            total=4,
        )
        storage_service = await StorageService.get_instance()
        await storage_service.configure(storage_config)

        # Create organizer
        organizer = StorageOrganizer(storage_service.manager)

        # Load and store files (recursively search subdirectories)
        emit_status_line(
            output_format=output_format,
            step="Scanning and storing synthetic data",
            index=3,
            total=4,
        )
        okh_files = list(data_dir.rglob("*okh*.json"))
        okw_files = list(data_dir.rglob("*okw*.json"))

        stored_files = []
        errors = []

        for file_path in okh_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)

                stored_path = await organizer.store_okh_manifest(
                    manifest_data, blob_name=file_path.name
                )
                stored_files.append(("OKH", file_path.name, stored_path))
                cli_ctx.log(
                    f"  ✅ Stored OKH: {file_path.name} -> {stored_path}", "success"
                )
            except Exception as e:
                error_msg = f"Failed to store {file_path.name}: {e}"
                errors.append(error_msg)
                cli_ctx.log(f"  ❌ {error_msg}", "error")

        for file_path in okw_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    facility_data = json.load(f)

                stored_path = await organizer.store_okw_facility(
                    facility_data, blob_name=file_path.name
                )
                stored_files.append(("OKW", file_path.name, stored_path))
                cli_ctx.log(
                    f"  ✅ Stored OKW: {file_path.name} -> {stored_path}", "success"
                )
            except Exception as e:
                error_msg = f"Failed to store {file_path.name}: {e}"
                errors.append(error_msg)
                cli_ctx.log(f"  ❌ {error_msg}", "error")

        emit_status_line(
            output_format=output_format,
            step="Rendering population summary",
            index=4,
            total=4,
        )
        if output_format == "json":
            output_data = {
                "status": "success" if not errors else "partial",
                "provider": provider,
                "bucket": storage_config.bucket_name,
                "files_stored": len(stored_files),
                "okh_count": len([f for f in stored_files if f[0] == "OKH"]),
                "okw_count": len([f for f in stored_files if f[0] == "OKW"]),
                "stored_files": [
                    {"type": f[0], "source": f[1], "destination": f[2]}
                    for f in stored_files
                ],
                "errors": errors,
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            if stored_files:
                cli_ctx.log(
                    f"✅ Populated {len(stored_files)} files into storage", "success"
                )
                cli_ctx.log(
                    f"  OKH files: {len([f for f in stored_files if f[0] == 'OKH'])}",
                    "info",
                )
                cli_ctx.log(
                    f"  OKW files: {len([f for f in stored_files if f[0] == 'OKW'])}",
                    "info",
                )
            if errors:
                cli_ctx.log(f"⚠️  {len(errors)} errors occurred", "warning")

        cli_ctx.end_command_tracking()

    except FileNotFoundError as e:
        cli_ctx.log(f"❌ {e}", "error")
        raise
    except StorageConfigError as e:
        cli_ctx.log(f"❌ Configuration error: {e}", "error")
        raise
    except Exception as e:
        cli_ctx.log(f"❌ Failed to populate storage: {e}", "error")
        raise
    finally:
        if storage_service is not None:
            await storage_service.cleanup()


@storage_group.group("config")
def config_group() -> None:
    """Read and change the storage backend of a running instance (#377).

    Storage used to be readable only from the environment the container
    started with. These commands act on the same persisted configuration the
    API writes, so an instance can be repointed after it is installed.
    """


@config_group.command("show")
@standard_cli_command(
    help_text="""
    Show the current storage configuration.

    Reports the configuration and, separately, what the app is actually
    connected to. The two can disagree — the configuration is what was asked
    for, the fingerprint is what answered — which is the first thing worth
    knowing when storage is misbehaving.

    Credential values are never printed; only which names are set.
    """,
    async_cmd=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,
)
@click.pass_context
async def config_show(
    ctx,
    verbose: bool,
    output_format: str,
    **_kwargs,
):
    """Show the storage configuration this instance is running on."""
    from ..core.services.storage_reconfigure import current_config

    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose
    cli_ctx.start_command_tracking("storage-config-show")

    storage_service = await StorageService.get_instance()
    view = await current_config(storage_service)
    fingerprint = await storage_service.get_config_fingerprint()

    if output_format == "json":
        click.echo(
            json.dumps({"config": view.to_dict(), "fingerprint": fingerprint}, indent=2)
        )
    else:
        cli_ctx.log("Storage configuration", "success")
        click.echo(f"  provider:    {view.provider}")
        click.echo(f"  bucket:      {view.bucket}")
        if view.region:
            click.echo(f"  region:      {view.region}")
        if view.endpoint_url:
            click.echo(f"  endpoint:    {view.endpoint_url}")
        click.echo(f"  credentials: {', '.join(view.credential_names) or 'none'}")
        click.echo(f"  source:      {view.source}")
        click.echo(f"  persisted:   {view.persisted}")
        click.echo(f"  connected:   {view.configured}")
        if fingerprint.get("error"):
            click.echo(f"  fingerprint: {fingerprint['error']}")
        else:
            click.echo(
                f"  contents:    {fingerprint.get('okh_count')} OKH, "
                f"{fingerprint.get('okw_count')} OKW"
            )

    cli_ctx.end_command_tracking()


@config_group.command("set")
@click.option(
    "--provider",
    type=click.Choice(["local", "gcs", "azure_blob", "aws_s3"]),
    required=True,
    help="Storage provider to switch to",
)
@click.option("--bucket", required=True, help="Bucket, container, or local path")
@click.option("--region", help="Region for cloud providers")
@click.option("--endpoint-url", help="Override endpoint, for S3-compatible backends")
@click.option(
    "--credential",
    "credentials",
    multiple=True,
    metavar="NAME=VALUE",
    help="Provider credential, repeatable. Names are checked per provider.",
)
@click.option(
    "--mode",
    type=click.Choice(["abandon", "migrate", "abandon_and_wipe"]),
    default="abandon",
    help="What happens to the data already in storage. Default: leave it.",
)
@click.option(
    "--wipe-confirm",
    metavar="BUCKET",
    help="Required for --mode abandon_and_wipe: the exact bucket being erased.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="For abandon_and_wipe: report what would be destroyed, change nothing.",
)
@standard_cli_command(
    help_text="""
    Switch this instance to a different storage backend.

    The new backend is validated before anything is committed: connect, write
    a probe object, read it back, then validate or initialize the directory
    structure. Only then is the configuration persisted and the running
    service swapped.

    A rejected configuration leaves the instance serving exactly as it was.

    Existing data is left where it is — this changes which backend is read and
    written, it does not move anything.
    """,
    epilog="""
    Examples:
      ohm storage config set --provider local --bucket ~/ohm-data

      ohm storage config set --provider azure_blob --bucket my-container \\
        --credential account_name=myaccount --credential account_key=secret
    """,
    async_cmd=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,
)
@click.pass_context
async def config_set(
    ctx,
    provider: str,
    bucket: str,
    region: Optional[str],
    endpoint_url: Optional[str],
    credentials: tuple,
    mode: str,
    wipe_confirm: Optional[str],
    dry_run: bool,
    verbose: bool,
    output_format: str,
    **_kwargs,
):
    """Validate a new storage backend, then switch to it."""
    from ..core.services.storage_reconfigure import (
        MODE_ABANDON_AND_WIPE,
        MODE_MIGRATE,
        StorageReconfigureError,
        build_candidate,
        ensure_configured,
        migrate_and_switch,
        reconfigure_storage,
        switch_and_wipe,
    )

    cli_ctx = ctx.obj
    cli_ctx.verbose = verbose
    cli_ctx.start_command_tracking("storage-config-set")

    parsed: Dict[str, str] = {}
    for item in credentials:
        name, sep, value = item.partition("=")
        if not sep or not name.strip():
            raise click.BadParameter(
                f"--credential expects NAME=VALUE, got {item!r}",
                param_hint="--credential",
            )
        parsed[name.strip()] = value

    storage_service = await StorageService.get_instance()
    # migrate and abandon_and_wipe act on the CURRENT backend, which a
    # freshly-started CLI process has not connected to yet.
    await ensure_configured(storage_service)
    try:
        candidate = build_candidate(
            provider=provider,
            bucket=bucket,
            region=region,
            endpoint_url=endpoint_url,
            credentials=parsed,
        )

        if mode == MODE_ABANDON_AND_WIPE:
            if not wipe_confirm:
                raise StorageReconfigureError(
                    "--mode abandon_and_wipe requires --wipe-confirm naming "
                    "the exact bucket to erase. Nothing was changed."
                )
            result = await switch_and_wipe(
                storage_service,
                candidate,
                wipe_confirm=wipe_confirm,
                dry_run=dry_run,
            )
        elif mode == MODE_MIGRATE:
            # Inline here, unlike the API. A CLI invocation is already a
            # long-running foreground process the operator is watching, so a
            # job would add a broker dependency and a polling loop to buy
            # nothing.
            result = await migrate_and_switch(
                storage_service,
                candidate,
                progress=lambda stage, fraction, message: cli_ctx.log(
                    f"{stage}: {message or ''} ({fraction:.0%})", "info"
                ),
            )
        else:
            result = await reconfigure_storage(
                storage_service,
                provider=candidate.provider,
                bucket=candidate.bucket_name,
                region=candidate.region,
                endpoint_url=candidate.endpoint_url,
                credentials=candidate.credentials,
            )
    except StorageReconfigureError as e:
        cli_ctx.log(
            f"{e} The instance is still serving from its previous configuration.",
            "error",
        )
        raise SystemExit(1) from e

    if output_format == "json":
        click.echo(json.dumps(result, indent=2))
    elif result.get("dry_run"):
        wipe = result.get("wipe", {})
        cli_ctx.log(
            f"Dry run: would delete {wipe.get('objects', 0)} object(s), "
            f"{wipe.get('bytes', 0)} bytes. Nothing was changed.",
            "success",
        )
        for key in wipe.get("keys", [])[:20]:
            click.echo(f"  - {key}")
        if wipe.get("keys_truncated"):
            click.echo("  … (truncated)")
    else:
        # `.get` throughout: a dry run and a wipe carry different keys, and
        # indexing would turn a mode that worked into a KeyError at the point
        # of reporting it.
        cli_ctx.log(
            f"Storage is now {result['provider']}: {result['bucket']}", "success"
        )
        if result.get("migration"):
            migration = result["migration"]
            click.echo(
                f"  migrated: {migration['objects_copied']} object(s), "
                f"{migration['objects_verified']} verified"
            )
        if result.get("prefixes_created"):
            click.echo(f"  created:  {', '.join(result['prefixes_created'])}")
        if result.get("prefixes_found"):
            click.echo(f"  present:  {', '.join(result['prefixes_found'])}")
        if result.get("wipe"):
            click.echo(
                f"  wiped:    {result['wipe']['objects']} object(s) from the "
                "previous backend"
            )
        elif result.get("previous_provider"):
            click.echo(
                f"  previous: {result['previous_provider']} "
                f"({result['previous_bucket']}) — data left in place"
            )

    cli_ctx.end_command_tracking()
