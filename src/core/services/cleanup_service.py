"""
Cleanup/optimization utilities for OKH project directories.

Goals (initial version):
- Remove unmodified documentation stubs created by the scaffold generator
- Remove empty directories left after users delete placeholder files

Design notes:
- Stub detection is content-based by regenerating known stub templates from
  ScaffoldService and comparing exact file contents. This avoids accidental
  deletion of user-modified files.
- Operations support dry-run to preview changes safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class CleanupOptions:
    project_path: str
    remove_unmodified_stubs: bool = True
    remove_empty_directories: bool = True
    dry_run: bool = True


@dataclass
class CleanupResult:
    removed_files: List[str] = field(default_factory=list)
    removed_directories: List[str] = field(default_factory=list)
    bytes_saved: int = 0
    warnings: List[str] = field(default_factory=list)


class CleanupService:
    """Service to clean and optimize scaffolded OKH project directories."""

    async def clean(self, options: CleanupOptions) -> CleanupResult:
        root = Path(options.project_path).expanduser().resolve()
        result = CleanupResult()

        if not root.exists() or not root.is_dir():
            result.warnings.append(f"Path not found or not a directory: {root}")
            return result

        # Build known stub contents using ScaffoldService templates
        # Import locally to avoid cycles
        from src.core.services.scaffold_service import ScaffoldService, ScaffoldOptions

        # We do not need all options; use defaults and infer project name from folder
        scaffold = ScaffoldService()
        project_name = root.name
        scaffold_opts = ScaffoldOptions(
            project_name=project_name,
            template_level="standard",
        )

        # Create an in-memory structure and inject stubs to reproduce contents
        structure = scaffold._create_directory_blueprint(project_name, scaffold_opts)
        scaffold._inject_stub_documents(structure, scaffold_opts)

        # Map of relative file path -> expected stub content
        stub_map: Dict[str, str] = self._flatten_structure_to_stub_map(structure, project_name)

        # Pass 1: remove files that match stub content exactly (if enabled)
        if options.remove_unmodified_stubs:
            for rel_path, content in stub_map.items():
                file_path = root / rel_path
                if file_path.exists() and file_path.is_file():
                    try:
                        current = file_path.read_text(encoding="utf-8")
                    except Exception:
                        # Skip unreadable files rather than risk deletion
                        continue
                    if self._is_unmodified_stub(file_path, current, content):
                        size = file_path.stat().st_size
                        result.bytes_saved += size
                        result.removed_files.append(str(file_path))
                        if not options.dry_run:
                            try:
                                file_path.unlink(missing_ok=True)
                            except Exception as e:
                                result.warnings.append(f"Failed to remove {file_path}: {e}")

        # Pass 2: remove empty directories bottom-up (if enabled)
        if options.remove_empty_directories:
            # Collect all directories, deepest first
            dirs: List[Path] = sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
            for d in dirs:
                try:
                    # A directory is empty if it has no non-hidden entries after potential file deletions
                    if not any(d.iterdir()):
                        result.removed_directories.append(str(d))
                        if not options.dry_run:
                            d.rmdir()
                except Exception as e:
                    result.warnings.append(f"Failed to inspect/remove directory {d}: {e}")

        return result

    # -------- Helpers --------
    def _flatten_structure_to_stub_map(self, structure: Dict, root_name: str) -> Dict[str, str]:
        """Return mapping of relative file paths to expected stub contents.

        Only includes files with non-empty string content in the blueprint.
        The manifest file is excluded because its content in projects is expected
        to be user-modified. We skip empty strings to avoid deleting intentionally
        blank files.
        """
        mapping: Dict[str, str] = {}

        def walk(node: Dict, prefix: Tuple[str, ...]) -> None:
            for name, child in node.items():
                if isinstance(child, dict):
                    walk(child, prefix + (name,))
                else:
                    if name == "okh-manifest.json":
                        continue
                    if isinstance(child, str) and child:
                        rel = "/".join(prefix + (name,))
                        # Strip top-level root dir from path if present at start
                        if rel.startswith(root_name + "/"):
                            rel = rel[len(root_name) + 1 :]
                        mapping[rel] = child

        # structure has a single root key
        root_key = next(iter(structure.keys()))
        walk(structure[root_key], (root_key,))
        return mapping

    def _is_unmodified_stub(self, file_path: Path, current: str, stub: str) -> bool:
        """Return True if file content matches a generated stub.

        Handles files with variable tokens (e.g., README title uses project name)
        by applying file-specific normalization before comparison.
        """
        if current == stub:
            return True

        name = file_path.name.lower()
        if name == "readme.md":
            def strip_title(s: str) -> str:
                lines = s.splitlines()
                # Remove first markdown header line starting with '# '
                if lines and lines[0].lstrip().startswith('# '):
                    lines = lines[1:]
                return "\n".join(lines).strip()

            return strip_title(current) == strip_title(stub)

        return False


