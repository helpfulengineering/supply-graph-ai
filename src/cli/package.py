import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
import click
import httpx

from ..core.models.okh import OKHManifest
from ..core.models.package import BuildOptions
from ..core.services.package_service import PackageService


@click.group()
def package():
    """OKH Package Management Commands"""
    pass


@package.command()
@click.argument('manifest_file', type=click.Path(exists=True))
@click.option('--output-dir', '-o', help='Output directory for built packages')
@click.option('--no-design-files', is_flag=True, help='Exclude design files')
@click.option('--no-manufacturing-files', is_flag=True, help='Exclude manufacturing files')
@click.option('--no-making-instructions', is_flag=True, help='Exclude making instructions')
@click.option('--no-software', is_flag=True, help='Exclude software')
@click.option('--no-parts', is_flag=True, help='Exclude parts')
@click.option('--no-operating-instructions', is_flag=True, help='Exclude operating instructions')
@click.option('--no-quality-instructions', is_flag=True, help='Exclude quality instructions')
@click.option('--no-risk-assessment', is_flag=True, help='Exclude risk assessment')
@click.option('--no-schematics', is_flag=True, help='Exclude schematics')
@click.option('--no-tool-settings', is_flag=True, help='Exclude tool settings')
@click.option('--no-verify', is_flag=True, help='Skip download verification')
@click.option('--max-concurrent', default=5, help='Maximum concurrent downloads')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def build(
    manifest_file: str,
    output_dir: Optional[str],
    no_design_files: bool,
    no_manufacturing_files: bool,
    no_making_instructions: bool,
    no_software: bool,
    no_parts: bool,
    no_operating_instructions: bool,
    no_quality_instructions: bool,
    no_risk_assessment: bool,
    no_schematics: bool,
    no_tool_settings: bool,
    no_verify: bool,
    max_concurrent: int,
    verbose: bool
):
    """Build an OKH package from a manifest file"""
    
    async def _build():
        try:
            # Load manifest
            manifest_path = Path(manifest_file)
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            manifest = OKHManifest.from_dict(manifest_data)
            
            if verbose:
                click.echo(f"Building package for: {manifest.title} v{manifest.version}")
                click.echo(f"Package name: {manifest.get_package_name()}")
            
            # Create build options
            options = BuildOptions(
                include_design_files=not no_design_files,
                include_manufacturing_files=not no_manufacturing_files,
                include_making_instructions=not no_making_instructions,
                include_software=not no_software,
                include_parts=not no_parts,
                include_operating_instructions=not no_operating_instructions,
                include_quality_instructions=not no_quality_instructions,
                include_risk_assessment=not no_risk_assessment,
                include_schematics=not no_schematics,
                include_tool_settings=not no_tool_settings,
                verify_downloads=not no_verify,
                max_concurrent_downloads=max_concurrent,
                output_dir=output_dir
            )
            
            # Build package
            package_service = await PackageService.get_instance()
            metadata = await package_service.build_package_from_manifest(manifest, options)
            
            # Display results
            click.echo(f"✅ Package built successfully!")
            click.echo(f"📦 Package: {metadata.package_name}/{metadata.version}")
            click.echo(f"📁 Location: {metadata.package_path}")
            click.echo(f"📄 Files: {metadata.total_files}")
            click.echo(f"💾 Size: {metadata.total_size_bytes:,} bytes")
            
            if verbose:
                click.echo("\n📋 File inventory:")
                for file_info in metadata.file_inventory:
                    click.echo(f"  - {file_info.local_path} ({file_info.size_bytes} bytes)")
            
        except Exception as e:
            click.echo(f"❌ Error building package: {e}", err=True)
            if verbose:
                import traceback
                click.echo(traceback.format_exc(), err=True)
            sys.exit(1)
    
    asyncio.run(_build())


@package.command()
@click.argument('manifest_id')
@click.option('--output-dir', '-o', help='Output directory for built packages')
@click.option('--no-design-files', is_flag=True, help='Exclude design files')
@click.option('--no-manufacturing-files', is_flag=True, help='Exclude manufacturing files')
@click.option('--no-making-instructions', is_flag=True, help='Exclude making instructions')
@click.option('--no-software', is_flag=True, help='Exclude software')
@click.option('--no-parts', is_flag=True, help='Exclude parts')
@click.option('--no-operating-instructions', is_flag=True, help='Exclude operating instructions')
@click.option('--no-quality-instructions', is_flag=True, help='Exclude quality instructions')
@click.option('--no-risk-assessment', is_flag=True, help='Exclude risk assessment')
@click.option('--no-schematics', is_flag=True, help='Exclude schematics')
@click.option('--no-tool-settings', is_flag=True, help='Exclude tool settings')
@click.option('--no-verify', is_flag=True, help='Skip download verification')
@click.option('--max-concurrent', default=5, help='Maximum concurrent downloads')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def build_from_storage(
    manifest_id: str,
    output_dir: Optional[str],
    no_design_files: bool,
    no_manufacturing_files: bool,
    no_making_instructions: bool,
    no_software: bool,
    no_parts: bool,
    no_operating_instructions: bool,
    no_quality_instructions: bool,
    no_risk_assessment: bool,
    no_schematics: bool,
    no_tool_settings: bool,
    no_verify: bool,
    max_concurrent: int,
    verbose: bool
):
    """Build an OKH package from a manifest stored in the system"""
    
    async def _build():
        try:
            from uuid import UUID
            
            # Parse manifest ID
            try:
                manifest_uuid = UUID(manifest_id)
            except ValueError:
                click.echo(f"❌ Invalid manifest ID format: {manifest_id}", err=True)
                sys.exit(1)
            
            if verbose:
                click.echo(f"Building package from stored manifest: {manifest_id}")
            
            # Create build options
            options = BuildOptions(
                include_design_files=not no_design_files,
                include_manufacturing_files=not no_manufacturing_files,
                include_making_instructions=not no_making_instructions,
                include_software=not no_software,
                include_parts=not no_parts,
                include_operating_instructions=not no_operating_instructions,
                include_quality_instructions=not no_quality_instructions,
                include_risk_assessment=not no_risk_assessment,
                include_schematics=not no_schematics,
                include_tool_settings=not no_tool_settings,
                verify_downloads=not no_verify,
                max_concurrent_downloads=max_concurrent,
                output_dir=output_dir
            )
            
            # Build package
            package_service = await PackageService.get_instance()
            metadata = await package_service.build_package_from_storage(manifest_uuid, options)
            
            # Display results
            click.echo(f"✅ Package built successfully!")
            click.echo(f"📦 Package: {metadata.package_name}/{metadata.version}")
            click.echo(f"📁 Location: {metadata.package_path}")
            click.echo(f"📄 Files: {metadata.total_files}")
            click.echo(f"💾 Size: {metadata.total_size_bytes:,} bytes")
            
            if verbose:
                click.echo("\n📋 File inventory:")
                for file_info in metadata.file_inventory:
                    click.echo(f"  - {file_info.local_path} ({file_info.size_bytes} bytes)")
            
        except Exception as e:
            click.echo(f"❌ Error building package: {e}", err=True)
            if verbose:
                import traceback
                click.echo(traceback.format_exc(), err=True)
            sys.exit(1)
    
    asyncio.run(_build())


@package.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def list_packages(verbose: bool):
    """List all built packages"""
    
    async def _list():
        try:
            package_service = await PackageService.get_instance()
            packages = await package_service.list_built_packages()
            
            if not packages:
                click.echo("No packages found.")
                return
            
            click.echo(f"Found {len(packages)} built packages:")
            click.echo()
            
            for metadata in packages:
                click.echo(f"📦 {metadata.package_name}/{metadata.version}")
                click.echo(f"   📁 {metadata.package_path}")
                click.echo(f"   📄 {metadata.total_files} files, {metadata.total_size_bytes:,} bytes")
                click.echo(f"   🕒 Built: {metadata.build_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if verbose:
                    click.echo(f"   🆔 Manifest ID: {metadata.okh_manifest_id}")
                    click.echo(f"   🔧 OME Version: {metadata.ome_version}")
                
                click.echo()
            
        except Exception as e:
            click.echo(f"❌ Error listing packages: {e}", err=True)
            if verbose:
                import traceback
                click.echo(traceback.format_exc(), err=True)
            sys.exit(1)
    
    asyncio.run(_list())


@package.command()
@click.argument('package_name')
@click.argument('version')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def verify(package_name: str, version: str, verbose: bool):
    """Verify a built package's integrity"""
    
    async def _verify():
        try:
            package_service = await PackageService.get_instance()
            results = await package_service.verify_package(package_name, version)
            
            if results["valid"]:
                click.echo(f"✅ Package {package_name}/{version} is valid")
                click.echo(f"📄 {results['total_files']} files, {results['total_size_bytes']:,} bytes")
            else:
                click.echo(f"❌ Package {package_name}/{version} has issues:")
                
                if results.get("missing_files"):
                    click.echo(f"   Missing files: {len(results['missing_files'])}")
                    if verbose:
                        for file in results["missing_files"]:
                            click.echo(f"     - {file}")
                
                if results.get("corrupted_files"):
                    click.echo(f"   Corrupted files: {len(results['corrupted_files'])}")
                    if verbose:
                        for file in results["corrupted_files"]:
                            click.echo(f"     - {file}")
                
                if results.get("extra_files"):
                    click.echo(f"   Extra files: {len(results['extra_files'])}")
                    if verbose:
                        for file in results["extra_files"]:
                            click.echo(f"     - {file}")
            
        except Exception as e:
            click.echo(f"❌ Error verifying package: {e}", err=True)
            if verbose:
                import traceback
                click.echo(traceback.format_exc(), err=True)
            sys.exit(1)
    
    asyncio.run(_verify())


@package.command()
@click.argument('package_name')
@click.argument('version')
@click.option('--force', '-f', is_flag=True, help='Force deletion without confirmation')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def delete(package_name: str, version: str, force: bool, verbose: bool):
    """Delete a built package"""
    
    async def _delete():
        try:
            if not force:
                if not click.confirm(f"Are you sure you want to delete package {package_name}/{version}?"):
                    click.echo("Deletion cancelled.")
                    return
            
            package_service = await PackageService.get_instance()
            success = await package_service.delete_package(package_name, version)
            
            if success:
                click.echo(f"✅ Package {package_name}/{version} deleted successfully")
            else:
                click.echo(f"❌ Failed to delete package {package_name}/{version}")
                sys.exit(1)
            
        except Exception as e:
            click.echo(f"❌ Error deleting package: {e}", err=True)
            if verbose:
                import traceback
                click.echo(traceback.format_exc(), err=True)
            sys.exit(1)
    
    asyncio.run(_delete())


if __name__ == '__main__':
    package()
