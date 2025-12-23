#!/usr/bin/env python3
"""
Generate an Aider-style repository map.
Aider's approach: Tree structure with files and their key symbols (classes, functions).
Token-conscious, hierarchical view.
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set
import subprocess


def get_git_files(repo_path: Path) -> List[Path]:
    """Get all tracked Python files from git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files', '*.py'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        files = [repo_path / f for f in result.stdout.strip().split('\n') if f]
        return files
    except subprocess.CalledProcessError:
        # Fallback to walking if not a git repo
        return list(repo_path.rglob('*.py'))


def extract_symbols(file_path: Path) -> Dict[str, List[str]]:
    """Extract classes and functions from a Python file using AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        classes = []
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get class methods
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                if methods:
                    classes.append(f"{node.name} ({', '.join(methods[:3])}{'...' if len(methods) > 3 else ''})")
                else:
                    classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                # Only top-level functions (not methods)
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    functions.append(node.name)
        
        # Get top-level functions more accurately
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        
        return {'classes': classes, 'functions': functions}
    except Exception as e:
        return {'classes': [], 'functions': [], 'error': str(e)}


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
            if 'classes' in content or 'functions' in content:
                # It's a file
                lines.append(f"{prefix}{current_prefix}{name}")
                
                # Add symbols
                if content.get('classes'):
                    for cls in content['classes']:
                        lines.append(f"{prefix}{'    ' if is_last else '│   '}    class {cls}")
                if content.get('functions'):
                    for func in content['functions']:
                        lines.append(f"{prefix}{'    ' if is_last else '│   '}    def {func}()")
                if content.get('error'):
                    lines.append(f"{prefix}{'    ' if is_last else '│   '}    # Error: {content['error']}")
            else:
                # It's a directory
                lines.append(f"{prefix}{current_prefix}{name}/")
                next_prefix = prefix + ("    " if is_last else "│   ")
                lines.append(format_tree(content, indent + 1, next_prefix))
    
    return '\n'.join(lines)


def generate_aider_map(repo_path: str) -> str:
    """Generate an Aider-style repository map."""
    repo_path = Path(repo_path)
    
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
    
    return '\n'.join(output)


if __name__ == '__main__':
    repo_path = Path(__file__).parent
    map_content = generate_aider_map(repo_path)
    
    # Save to file
    output_file = repo_path / '.repo-map-aider.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(map_content)
    
    print(f"Aider-style repository map generated: {output_file}")
    print(f"\nPreview (first 50 lines):")
    print('\n'.join(map_content.split('\n')[:50]))
