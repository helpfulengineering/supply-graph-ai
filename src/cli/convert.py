"""
Convert commands for OHM CLI.

Provides bi-directional conversion between OKH manifests and external
document formats.  Currently supports conversion to/from the MSF
(Maker Space Foundation) 3D-printed product technical specification
datasheet (.docx).
"""

import json
from pathlib import Path
from typing import Optional

import click

from ..core.models.okh import OKHManifest
from ..core.services.datasheet_converter import (
    DatasheetConversionError,
    DatasheetConverter,
)
from .base import CLIContext
from .decorators import standard_cli_command


@click.group()
def convert_group():
    """
    Format conversion commands for OHM.

    Convert between OKH manifests and external document formats used
    in the open hardware ecosystem.

    Supported formats:
      - MSF Datasheet (.docx): 3D-printed product technical specification

    The internal OKH data model is always the canonical source of truth.

    Examples:
      # Convert OKH manifest to MSF datasheet
      ohm convert to-datasheet my-project.okh.json -o my-project-datasheet.docx

      # Convert MSF datasheet back to OKH manifest
      ohm convert from-datasheet my-project-datasheet.docx -o my-project.okh.json

      # Convert with custom template
      ohm convert to-datasheet my-project.okh.json --template custom-template.docx
    """
    pass


@convert_group.command("to-datasheet")
@click.argument("manifest_file", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(),
    help="Output .docx file path. Defaults to <manifest_name>-datasheet.docx",
)
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to a custom MSF datasheet template (.docx)",
)
@standard_cli_command(
    help_text="""
    Convert an OKH manifest to an MSF datasheet (.docx).

    Reads an OKH manifest (JSON or YAML) and populates the MSF 3D-printed
    product technical specification datasheet template with the manifest
    data.

    The OKH manifest is the canonical source of truth.  Fields that do
    not have a direct mapping in the datasheet template are stored in
    the OKH metadata dict and round-tripped where possible.
    """,
    epilog="""
    Examples:
      # Basic conversion
      ohm convert to-datasheet my-project.okh.json

      # Specify output path
      ohm convert to-datasheet my-project.okh.json -o output/datasheet.docx

      # Use a custom template
      ohm convert to-datasheet my-project.okh.json --template my-template.docx
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,
)
@click.pass_context
async def to_datasheet(
    ctx,
    manifest_file: str,
    output_path: Optional[str],
    template_path: Optional[str],
    verbose: bool,
    output_format: str,
    **kwargs,
):
    """Convert an OKH manifest to an MSF datasheet."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.start_command_tracking("convert-to-datasheet")
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose

    try:
        # Read manifest file
        cli_ctx.log("Reading OKH manifest...", "info")
        manifest_path = Path(manifest_file)

        with open(manifest_path, "r") as f:
            if manifest_path.suffix.lower() in [".yaml", ".yml"]:
                import yaml

                manifest_data = yaml.safe_load(f)
            else:
                manifest_data = json.load(f)

        # Parse into canonical OKHManifest
        manifest = OKHManifest.from_dict(manifest_data)
        cli_ctx.log(f"Loaded manifest: {manifest.title} (v{manifest.version})", "info")

        # Determine output path
        if not output_path:
            stem = manifest_path.stem.replace(".okh", "")
            output_path = str(manifest_path.parent / f"{stem}-datasheet.docx")

        # Convert
        cli_ctx.log("Converting to MSF datasheet format...", "info")
        converter = DatasheetConverter(template_path=template_path)
        result_path = converter.okh_to_datasheet(manifest, output_path)

        cli_ctx.log(f"Datasheet written to: {result_path}", "success")

        if output_format == "json":
            click.echo(
                json.dumps(
                    {
                        "status": "success",
                        "output_path": result_path,
                        "manifest_title": manifest.title,
                        "manifest_version": manifest.version,
                    },
                    indent=2,
                )
            )

    except DatasheetConversionError as exc:
        cli_ctx.log(f"Conversion error: {exc}", "error")
        raise click.ClickException(str(exc))
    except Exception as exc:
        cli_ctx.log(f"Unexpected error: {exc}", "error")
        raise click.ClickException(str(exc))


@convert_group.command("from-datasheet")
@click.argument("docx_file", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(),
    help="Output .okh.json file path. Defaults to <docx_name>.okh.json",
)
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to a custom MSF datasheet template (.docx) for validation",
)
@click.option(
    "--format",
    "file_format",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Output file format (default: json)",
)
@standard_cli_command(
    help_text="""
    Convert an MSF datasheet (.docx) to an OKH manifest.

    Parses a populated MSF 3D-printed product technical specification
    datasheet and produces a canonical OKH manifest in JSON or YAML
    format.

    The resulting manifest can be used directly with all other OHM
    commands (validate, package, match, etc.).
    """,
    epilog="""
    Examples:
      # Basic conversion
      ohm convert from-datasheet my-datasheet.docx

      # Output as YAML
      ohm convert from-datasheet my-datasheet.docx --format yaml

      # Specify output path
      ohm convert from-datasheet my-datasheet.docx -o my-project.okh.json
    """,
    async_cmd=True,
    track_performance=True,
    handle_errors=True,
    format_output=True,
    add_llm_config=False,
)
@click.pass_context
async def from_datasheet(
    ctx,
    docx_file: str,
    output_path: Optional[str],
    template_path: Optional[str],
    file_format: str,
    verbose: bool,
    output_format: str,
    **kwargs,
):
    """Convert an MSF datasheet to an OKH manifest."""
    cli_ctx: CLIContext = ctx.obj
    cli_ctx.start_command_tracking("convert-from-datasheet")
    cli_ctx.verbose = verbose
    cli_ctx.config.verbose = verbose

    try:
        cli_ctx.log("Reading MSF datasheet...", "info")

        # Parse datasheet
        converter = DatasheetConverter(template_path=template_path)
        manifest = converter.datasheet_to_okh(docx_file)

        cli_ctx.log(f"Parsed manifest: {manifest.title}", "info")

        # Determine output path
        if not output_path:
            docx_path = Path(docx_file)
            stem = docx_path.stem.replace("-datasheet", "")
            ext = "yaml" if file_format == "yaml" else "json"
            output_path = str(docx_path.parent / f"{stem}.okh.{ext}")

        # Serialize
        manifest_dict = manifest.to_dict()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if file_format == "yaml":
            import yaml

            with open(output_path, "w") as f:
                yaml.dump(manifest_dict, f, default_flow_style=False, sort_keys=False)
        else:
            with open(output_path, "w") as f:
                json.dump(manifest_dict, f, indent=2, default=str)

        cli_ctx.log(f"OKH manifest written to: {output_path}", "success")

        if output_format == "json":
            click.echo(
                json.dumps(
                    {
                        "status": "success",
                        "output_path": output_path,
                        "manifest_title": manifest.title,
                        "format": file_format,
                    },
                    indent=2,
                )
            )

    except DatasheetConversionError as exc:
        cli_ctx.log(f"Conversion error: {exc}", "error")
        raise click.ClickException(str(exc))
    except Exception as exc:
        cli_ctx.log(f"Unexpected error: {exc}", "error")
        raise click.ClickException(str(exc))
