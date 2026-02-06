"""
Storage management commands for OHM CLI

This module provides commands for setting up and managing storage systems,
including directory structure creation and data population.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import click

from ..config.storage_config import (
    StorageConfig,
    StorageConfigError,
    create_storage_config,
)
from ..core.services.storage_service import StorageService
from ..core.storage.organizer import StorageOrganizer
from ..core.utils.logging import get_logger
from .base import CLIContext
from .decorators import standard_cli_command

logger = get_logger(__name__)


@click.group()
def storage_group():
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
        storage_service = await StorageService.get_instance()
        await storage_service.configure(storage_config)

        # Create organizer and setup structure
        organizer = StorageOrganizer(storage_service.manager)
        result = await organizer.create_directory_structure()

        if output_format == "json":
            # Include absolute path for local storage
            storage_location = storage_config.bucket_name
            if provider == "local":
                from pathlib import Path

                storage_location = str(Path(storage_config.bucket_name).resolve())

            output_data = {
                "status": "success",
                "provider": provider,
                "bucket": storage_config.bucket_name,
                "storage_location": storage_location,
                "region": region,
                "directories_created": result["total_created"],
                "directories": result["created_directories"],
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            cli_ctx.log(
                "✅ Storage directory structure created successfully!", "success"
            )
            cli_ctx.log(f"Provider: {provider}", "info")

            # Show full path for local storage
            if provider == "local":
                from pathlib import Path

                abs_path = Path(storage_config.bucket_name).resolve()
                cli_ctx.log(f"Location: {abs_path}", "info")
            else:
                cli_ctx.log(f"Bucket: {storage_config.bucket_name}", "info")
                if region:
                    cli_ctx.log(f"Region: {region}", "info")

            cli_ctx.log(f"Created {result['total_created']} directories:", "info")
            for directory in result["created_directories"]:
                click.echo(f"  - {directory}")

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

    try:
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
        storage_service = await StorageService.get_instance()
        await storage_service.configure(storage_config)

        # Create organizer
        organizer = StorageOrganizer(storage_service.manager)

        # Load and store files (recursively search subdirectories)
        okh_files = list(data_dir.rglob("*okh*.json"))
        okw_files = list(data_dir.rglob("*okw*.json"))

        stored_files = []
        errors = []

        for file_path in okh_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)

                stored_path = await organizer.store_okh_manifest(manifest_data)
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

                stored_path = await organizer.store_okw_facility(facility_data)
                stored_files.append(("OKW", file_path.name, stored_path))
                cli_ctx.log(
                    f"  ✅ Stored OKW: {file_path.name} -> {stored_path}", "success"
                )
            except Exception as e:
                error_msg = f"Failed to store {file_path.name}: {e}"
                errors.append(error_msg)
                cli_ctx.log(f"  ❌ {error_msg}", "error")

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
