"""
Built Directory Export functionality for OKH manifests and BOMs.

This module provides functionality to export generated manifests and BOMs
to a structured built directory with multiple formats for different use cases.
"""

import json
from pathlib import Path
from typing import Dict, Any
from ..models.bom import BillOfMaterials


class BuiltDirectoryExporter:
    """Export generated manifests and BOMs to built directory structure"""

    def __init__(self, output_dir: Path):
        """
        Initialize the built directory exporter.

        Args:
            output_dir: Base output directory for built files
        """
        self.output_dir = output_dir
        self.bom_dir = output_dir / "bom"
        self.docs_dir = output_dir / "docs"

    async def export_manifest_with_bom(
        self, manifest: Dict[str, Any], bom: BillOfMaterials
    ):
        """
        Export OKH manifest with BOM to built directory.

        Args:
            manifest: OKH manifest dictionary
            bom: BillOfMaterials object
        """
        # Export main manifest
        manifest_path = self.output_dir / "manifest.okh.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        # Export BOM in multiple formats
        await self._export_bom_formats(bom)

        # Export documentation
        await self._export_bom_documentation(bom)

    async def _export_bom_formats(self, bom: BillOfMaterials):
        """
        Export BOM in multiple formats.

        Args:
            bom: BillOfMaterials object to export
        """
        self.bom_dir.mkdir(exist_ok=True)

        # JSON format (structured)
        bom_json_path = self.bom_dir / "bom.json"
        with open(bom_json_path, "w") as f:
            json.dump(bom.to_dict(), f, indent=2)

        # Markdown format (human-readable)
        bom_md_path = self.bom_dir / "bom.md"
        with open(bom_md_path, "w") as f:
            f.write(self._bom_to_markdown(bom))

        # CSV format (spreadsheet-compatible)
        bom_csv_path = self.bom_dir / "bom.csv"
        with open(bom_csv_path, "w") as f:
            f.write(self._bom_to_csv(bom))

        # Individual component files
        components_dir = self.bom_dir / "components"
        components_dir.mkdir(exist_ok=True)

        for component in bom.components:
            component_path = components_dir / f"{component.id}.json"
            with open(component_path, "w") as f:
                json.dump(component.to_dict(), f, indent=2)

    async def _export_bom_documentation(self, bom: BillOfMaterials):
        """
        Export BOM documentation.

        Args:
            bom: BillOfMaterials object
        """
        self.docs_dir.mkdir(exist_ok=True)

        # BOM summary
        summary_path = self.docs_dir / "bom_summary.md"
        with open(summary_path, "w") as f:
            f.write(self._bom_to_summary(bom))

        # Component catalog
        catalog_path = self.docs_dir / "component_catalog.md"
        with open(catalog_path, "w") as f:
            f.write(self._bom_to_catalog(bom))

    def _bom_to_markdown(self, bom: BillOfMaterials) -> str:
        """
        Convert BOM to Markdown format.

        Args:
            bom: BillOfMaterials object

        Returns:
            Markdown formatted string
        """
        lines = [
            f"# {bom.name}",
            "",
            f"**Generated:** {bom.metadata.get('generated_at', 'Unknown')}",
            f"**Components:** {len(bom.components)}",
            f"**Sources:** {bom.metadata.get('source_count', 0)}",
            "",
            "## Components",
            "",
            "| ID | Name | Quantity | Unit | Source | Confidence |",
            "|----|------|----------|------|--------|------------|",
        ]

        for comp in bom.components:
            lines.append(
                f"| {comp.id} | {comp.name} | {comp.quantity} | {comp.unit} | "
                f"{comp.metadata.get('source', '')} | {comp.metadata.get('confidence', 0):.2f} |"
            )

        return "\n".join(lines)

    def _bom_to_csv(self, bom: BillOfMaterials) -> str:
        """
        Convert BOM to CSV format.

        Args:
            bom: BillOfMaterials object

        Returns:
            CSV formatted string
        """
        lines = ["ID,Name,Quantity,Unit,Source,Confidence,File_Reference"]
        for comp in bom.components:
            lines.append(
                f"{comp.id},{comp.name},{comp.quantity},{comp.unit},"
                f"{comp.metadata.get('source', '')},{comp.metadata.get('confidence', 0):.2f},"
                f"{comp.metadata.get('file_reference', '')}"
            )
        return "\n".join(lines)

    def _bom_to_summary(self, bom: BillOfMaterials) -> str:
        """
        Convert BOM to summary format.

        Args:
            bom: BillOfMaterials object

        Returns:
            Summary formatted string
        """
        total_components = len(bom.components)
        total_quantity = sum(comp.quantity for comp in bom.components)
        sources = set(comp.metadata.get("source", "") for comp in bom.components)

        lines = [
            f"# {bom.name} - Summary",
            "",
            f"**Total Components:** {total_components}",
            f"**Total Quantity:** {total_quantity}",
            f"**Sources:** {', '.join(sources)}",
            f"**Generated:** {bom.metadata.get('generated_at', 'Unknown')}",
            "",
            "## Quick Overview",
            "",
        ]

        # Group by source
        by_source = {}
        for comp in bom.components:
            source = comp.metadata.get("source", "unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(comp)

        for source, components in by_source.items():
            lines.append(f"### {source.replace('_', ' ').title()}")
            for comp in components:
                lines.append(f"- {comp.quantity} {comp.unit} {comp.name}")
            lines.append("")

        return "\n".join(lines)

    def _bom_to_catalog(self, bom: BillOfMaterials) -> str:
        """
        Convert BOM to component catalog format.

        Args:
            bom: BillOfMaterials object

        Returns:
            Catalog formatted string
        """
        lines = [
            f"# {bom.name} - Component Catalog",
            "",
            f"**Generated:** {bom.metadata.get('generated_at', 'Unknown')}",
            f"**Total Components:** {len(bom.components)}",
            "",
            "## Component Details",
            "",
        ]

        for comp in bom.components:
            lines.extend(
                [
                    f"### {comp.name}",
                    f"**ID:** {comp.id}",
                    f"**Quantity:** {comp.quantity} {comp.unit}",
                    f"**Source:** {comp.metadata.get('source', 'unknown')}",
                    f"**Confidence:** {comp.metadata.get('confidence', 0):.2f}",
                ]
            )

            if comp.metadata.get("file_reference"):
                lines.append(f"**File Reference:** {comp.metadata['file_reference']}")

            if comp.metadata.get("file_path"):
                lines.append(f"**Source File:** {comp.metadata['file_path']}")

            lines.append("")

        return "\n".join(lines)
