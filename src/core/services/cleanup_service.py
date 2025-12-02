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
import re


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
        stub_map: Dict[str, str] = self._flatten_structure_to_stub_map(
            structure, project_name
        )

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
                                result.warnings.append(
                                    f"Failed to remove {file_path}: {e}"
                                )

        # Pass 2: remove empty directories bottom-up (if enabled)
        if options.remove_empty_directories:
            # Collect all directories, deepest first
            dirs: List[Path] = sorted(
                (p for p in root.rglob("*") if p.is_dir()),
                key=lambda p: len(p.parts),
                reverse=True,
            )
            for d in dirs:
                try:
                    # A directory is empty if it has no non-hidden entries after potential file deletions
                    if not any(d.iterdir()):
                        result.removed_directories.append(str(d))
                        if not options.dry_run:
                            d.rmdir()
                except Exception as e:
                    result.warnings.append(
                        f"Failed to inspect/remove directory {d}: {e}"
                    )

        # Pass 3: detect broken links in remaining markdown files (if files were removed)
        if result.removed_files:
            broken_links = self._detect_broken_links(root, result.removed_files)
            if broken_links:
                for file_path, broken_link_targets in broken_links.items():
                    targets_str = ", ".join(broken_link_targets[:3])  # Limit to first 3
                    if len(broken_link_targets) > 3:
                        targets_str += f", ... ({len(broken_link_targets)} total)"
                    result.warnings.append(
                        f"Broken link(s) in {file_path}: {targets_str}"
                    )

        return result

    # -------- Helpers --------
    def _flatten_structure_to_stub_map(
        self, structure: Dict, root_name: str
    ) -> Dict[str, str]:
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
                if lines and lines[0].lstrip().startswith("# "):
                    lines = lines[1:]
                return "\n".join(lines).strip()

            return strip_title(current) == strip_title(stub)

        return False

    def _detect_broken_links(
        self, root: Path, removed_files: List[str]
    ) -> Dict[str, List[str]]:
        """Detect broken links in remaining markdown files after cleanup.

        Scans all remaining markdown files for links that point to files that
        were removed during cleanup. Returns a dictionary mapping file paths
        to lists of broken link targets.

        Args:
            root: Project root directory
            removed_files: List of file paths (strings) that were removed

        Returns:
            Dict mapping file_path (str) to list of broken link targets (str)
        """
        broken_links: Dict[str, List[str]] = {}

        # Create set of removed file paths for quick lookup
        # Normalize paths to handle both absolute and relative paths
        removed_paths = set()
        removed_file_names = set()

        for removed_file in removed_files:
            removed_path = Path(removed_file)

            # Add resolved absolute path
            try:
                if removed_path.is_absolute():
                    removed_paths.add(removed_path.resolve())
                else:
                    # Relative path - resolve relative to root
                    resolved = (root / removed_path).resolve()
                    removed_paths.add(resolved)
            except (ValueError, OSError):
                # Path resolution failed, skip
                pass

            # Add relative path from root for matching
            try:
                rel_path = (
                    removed_path.relative_to(root)
                    if removed_path.is_absolute()
                    else removed_path
                )
                removed_paths.add(rel_path)
            except ValueError:
                # Path not relative to root, skip
                pass

            removed_file_names.add(removed_path.name)

        # Scan all remaining markdown files
        for md_file in root.rglob("*.md"):
            # Skip files that were removed
            md_resolved = md_file.resolve()
            md_str = str(md_file)
            md_relative = None
            try:
                md_relative = md_file.relative_to(root)
            except ValueError:
                pass

            # Check if this file was removed (multiple checks for robustness)
            if (
                md_resolved in removed_paths
                or md_str in removed_files
                or str(md_resolved) in removed_files
                or (md_relative and md_relative in removed_paths)
            ):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                # Skip unreadable files
                continue

            # Extract markdown links: [text](path) or [text](path "title")
            # Pattern matches: [optional text](path with spaces or special chars)
            link_pattern = r"\[([^\]]*)\]\(([^)]+)\)"
            matches = re.findall(link_pattern, content)

            broken_targets = []
            for link_text, link_path in matches:
                # Remove title/query if present: path "title" -> path
                link_path = link_path.split('"')[0].strip()

                # Skip anchor links, external URLs, and empty paths
                if not link_path or link_path.startswith("#") or "://" in link_path:
                    continue

                # Resolve the link path relative to the markdown file's location
                try:
                    # Handle relative paths (../foo/bar.md)
                    if link_path.startswith("../") or link_path.startswith("./"):
                        link_resolved = (md_file.parent / link_path).resolve()
                    else:
                        # Relative path from file's directory
                        link_resolved = (md_file.parent / link_path).resolve()

                    # Check if the resolved path points to a removed file
                    if link_resolved in removed_paths:
                        broken_targets.append(link_path)
                    # Also check by filename (in case path resolution differs)
                    elif (
                        link_resolved.name in removed_file_names
                        and not link_resolved.exists()
                    ):
                        broken_targets.append(link_path)
                except (ValueError, OSError):
                    # Path resolution failed, check if filename matches removed files
                    link_file_name = Path(link_path).name
                    if link_file_name in removed_file_names:
                        # Only add if file doesn't exist (to avoid false positives)
                        test_path = md_file.parent / link_path
                        if not test_path.exists():
                            broken_targets.append(link_path)

            if broken_targets:
                # Use relative path from root for cleaner output
                try:
                    rel_file_path = md_file.relative_to(root)
                    broken_links[str(rel_file_path)] = broken_targets
                except ValueError:
                    broken_links[str(md_file)] = broken_targets

        return broken_links
