#!/usr/bin/env python3
"""
Generate repository maps in both Aider and Sourcegraph styles.
Combines both approaches into a single unified script.
"""

import ast
import argparse
from pathlib import Path
from typing import List, Dict
import subprocess


def get_git_files(repo_path: Path) -> List[Path]:
    """Get all tracked Python files from git, excluding test files."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.py"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        files = [repo_path / f for f in result.stdout.strip().split("\n") if f]
    except subprocess.CalledProcessError:
        # Fallback to walking if not a git repo
        files = list(repo_path.rglob("*.py"))

    # Filter out files in src/tests directory
    filtered_files = [f for f in files if "src/tests" not in str(f.relative_to(repo_path))]
    return filtered_files


# ============================================================================
# Aider-style map functions
# ============================================================================


def extract_symbols(file_path: Path) -> Dict[str, List[str]]:
    """Extract classes and functions from a Python file using AST."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        classes = []
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get class methods
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                if methods:
                    classes.append(
                        f"{node.name} ({', '.join(methods[:3])}{'...' if len(methods) > 3 else ''})"
                    )
                else:
                    classes.append(node.name)

        # Get top-level functions
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)

        return {"classes": classes, "functions": functions}
    except Exception as e:
        return {"classes": [], "functions": [], "error": str(e)}


def build_tree_structure(files: List[Path], repo_path: Path) -> Dict:
    """Build a hierarchical tree structure of the repository."""
    tree = {}

    for file_path in files:
        rel_path = file_path.relative_to(repo_path)
        parts = rel_path.parts

        current = tree
        for part in parts[:-1]:  # Navigate to parent directory
            if part not in current:
                current[part] = {}
            current = current[part]

        # Add file with its symbols
        current[parts[-1]] = extract_symbols(file_path)

    return tree


def format_tree(tree: Dict, indent: int = 0, prefix: str = "") -> str:
    """Format the tree structure as a readable string."""
    lines = []
    items = sorted(tree.items())

    for i, (name, content) in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "

        if isinstance(content, dict):
            if "classes" in content or "functions" in content:
                # It's a file
                lines.append(f"{prefix}{current_prefix}{name}")

                # Add symbols
                if content.get("classes"):
                    for cls in content["classes"]:
                        lines.append(f"{prefix}{'    ' if is_last else '│   '}    class {cls}")
                if content.get("functions"):
                    for func in content["functions"]:
                        lines.append(f"{prefix}{'    ' if is_last else '│   '}    def {func}()")
                if content.get("error"):
                    lines.append(
                        f"{prefix}{'    ' if is_last else '│   '}    # Error: {content['error']}"
                    )
            else:
                # It's a directory
                lines.append(f"{prefix}{current_prefix}{name}/")
                next_prefix = prefix + ("    " if is_last else "│   ")
                lines.append(format_tree(content, indent + 1, next_prefix))

    return "\n".join(lines)


def generate_aider_map(repo_path: Path) -> str:
    """Generate an Aider-style repository map."""
    # Header
    output = ["=" * 80]
    output.append("REPOSITORY MAP (Aider Style)")
    output.append("=" * 80)
    output.append(f"Repository: {repo_path.name}")
    output.append("")

    # Get files
    files = get_git_files(repo_path)
    output.append(f"Total Python files: {len(files)}")
    output.append("")

    # Build and format tree
    tree = build_tree_structure(files, repo_path)
    output.append(format_tree(tree))

    output.append("")
    output.append("=" * 80)

    return "\n".join(output)


# ============================================================================
# Sourcegraph-style map functions
# ============================================================================


def _get_name(node):
    """Helper to get name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Subscript):
        # Handle generic types like Generic[T], List[str], etc.
        # Extract just the base name (e.g., "Generic" from "Generic[T]")
        return _get_name(node.value)
    return f"<{node.__class__.__name__}>"  # Fallback for unknown node types


def extract_detailed_symbols(file_path: Path, repo_path: Path) -> Dict:
    """Extract detailed symbol information including imports and relationships."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))

        rel_path = str(file_path.relative_to(repo_path))

        symbols = {
            "path": rel_path,
            "imports": [],
            "classes": [],
            "functions": [],
            "exports": [],
            "docstring": ast.get_docstring(tree) or "",
        }

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    symbols["imports"].append({"module": alias.name, "alias": alias.asname})
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    symbols["imports"].append(
                        {"from": module, "name": alias.name, "alias": alias.asname}
                    )

        # Extract top-level definitions
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(
                            {
                                "name": item.name,
                                "params": [arg.arg for arg in item.args.args],
                                "is_public": not item.name.startswith("_"),
                            }
                        )

                symbols["classes"].append(
                    {
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "methods": methods,
                        "bases": [_get_name(base) for base in node.bases],
                        "is_public": not node.name.startswith("_"),
                    }
                )

                # Public classes are exports
                if not node.name.startswith("_"):
                    symbols["exports"].append(node.name)

            elif isinstance(node, ast.FunctionDef):
                symbols["functions"].append(
                    {
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "params": [arg.arg for arg in node.args.args],
                        "is_public": not node.name.startswith("_"),
                    }
                )

                # Public functions are exports
                if not node.name.startswith("_"):
                    symbols["exports"].append(node.name)

        return symbols
    except Exception as e:
        return {
            "path": str(file_path.relative_to(repo_path)),
            "error": str(e),
            "imports": [],
            "classes": [],
            "functions": [],
            "exports": [],
        }


def categorize_files(symbols_by_file: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize files by their role in the codebase."""
    categories = {
        "entry_points": [],
        "services": [],
        "models": [],
        "utilities": [],
        "configuration": [],
        "other": [],
    }

    for symbols in symbols_by_file:
        path = symbols["path"]

        if "__main__" in path or "main.py" in path or "run.py" in path:
            categories["entry_points"].append(symbols)
        elif "service" in path.lower():
            categories["services"].append(symbols)
        elif "model" in path.lower():
            categories["models"].append(symbols)
        elif "config" in path.lower() or "settings" in path.lower():
            categories["configuration"].append(symbols)
        elif "util" in path.lower() or "helper" in path.lower():
            categories["utilities"].append(symbols)
        else:
            categories["other"].append(symbols)

    return categories


def format_sourcegraph_map(categories: Dict[str, List[Dict]]) -> str:
    """Format the Sourcegraph-style map as markdown."""
    lines = ["# Repository Code Intelligence Map (Sourcegraph Style)", ""]

    # Overview section
    lines.append("## Overview")
    lines.append("")
    total_files = sum(len(files) for files in categories.values())
    lines.append(f"Total files analyzed: {total_files}")
    lines.append("")

    # Category sections
    for category, files in categories.items():
        if not files:
            continue

        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")

        for file_symbols in files:
            lines.append(f"### `{file_symbols['path']}`")

            if file_symbols.get("docstring"):
                lines.append(f"> {file_symbols['docstring'][:100]}...")

            lines.append("")

            # Exports
            if file_symbols.get("exports"):
                lines.append(f"**Exports:** {', '.join(file_symbols['exports'][:5])}")
                lines.append("")

            # Classes
            if file_symbols.get("classes"):
                lines.append("**Classes:**")
                for cls in file_symbols["classes"]:
                    public_methods = [m["name"] for m in cls["methods"] if m["is_public"]]
                    if cls.get("bases"):
                        lines.append(f"- `{cls['name']}` (inherits: {', '.join(cls['bases'])})")
                    else:
                        lines.append(f"- `{cls['name']}`")

                    if public_methods:
                        lines.append(f"  - Methods: {', '.join(public_methods[:5])}")

                    if cls.get("docstring"):
                        lines.append(f"  - {cls['docstring'][:80]}...")
                lines.append("")

            # Functions
            if file_symbols.get("functions"):
                public_funcs = [f for f in file_symbols["functions"] if f["is_public"]]
                if public_funcs:
                    lines.append("**Functions:**")
                    for func in public_funcs[:5]:
                        params = ", ".join(func["params"][:3])
                        lines.append(f"- `{func['name']}({params})`")
                        if func.get("docstring"):
                            lines.append(f"  - {func['docstring'][:80]}...")
                    lines.append("")

            # Key imports
            if file_symbols.get("imports"):
                internal_imports = [
                    imp
                    for imp in file_symbols["imports"]
                    if imp.get("from", "").startswith("src")
                    or imp.get("module", "").startswith("src")
                ]
                if internal_imports:
                    lines.append(f"**Internal Dependencies:** {len(internal_imports)} imports")
                    lines.append("")

            if file_symbols.get("error"):
                lines.append(f"⚠️ _Error parsing file: {file_symbols['error']}_")
                lines.append("")

    return "\n".join(lines)


def generate_sourcegraph_map(repo_path: Path) -> str:
    """Generate a Sourcegraph-style repository map."""
    # Get files
    files = get_git_files(repo_path)

    # Extract symbols from all files
    all_symbols = []
    for file_path in files:
        symbols = extract_detailed_symbols(file_path, repo_path)
        all_symbols.append(symbols)

    # Categorize and format
    categories = categorize_files(all_symbols)
    return format_sourcegraph_map(categories)


# ============================================================================
# Main function
# ============================================================================


def generate_combined_map(target_path: Path, output_path: Path) -> str:
    """Generate both Aider and Sourcegraph maps and combine them."""
    lines = []

    # Generate Aider map
    aider_map = generate_aider_map(target_path)
    lines.append(aider_map)
    lines.append("")
    lines.append("")

    # Generate Sourcegraph map
    sourcegraph_map = generate_sourcegraph_map(target_path)
    lines.append(sourcegraph_map)

    return "\n".join(lines)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate repository maps in both Aider and Sourcegraph styles"
    )
    parser.add_argument(
        "--target",
        type=str,
        default=".",
        help="Target directory to analyze (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".",
        help="Output directory for the map file (default: current directory)",
    )
    parser.add_argument(
        "--filename",
        type=str,
        default=".repo-map.md",
        help="Output filename (default: .repo-map.md)",
    )

    args = parser.parse_args()

    # Resolve paths
    target_path = Path(args.target).resolve()
    output_path = Path(args.output).resolve()
    output_file = output_path / args.filename

    # Validate target path
    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}")
        return 1

    if not target_path.is_dir():
        print(f"Error: Target path is not a directory: {target_path}")
        return 1

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate combined map
    print(f"Generating repository maps for: {target_path}")
    print(f"Output file: {output_file}")
    print()

    map_content = generate_combined_map(target_path, output_path)

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(map_content)

    print(f"✓ Combined repository map generated: {output_file}")
    print(f"\nPreview (first 50 lines):")
    print("\n".join(map_content.split("\n")[:50]))

    return 0


if __name__ == "__main__":
    exit(main())
