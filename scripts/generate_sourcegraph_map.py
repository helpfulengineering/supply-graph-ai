#!/usr/bin/env python3
"""
Generate a Sourcegraph-style repository map.
Sourcegraph's approach: Hierarchical symbol extraction with relationships,
focusing on code intelligence (imports, exports, definitions).
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Tuple
import subprocess
import json


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
        return list(repo_path.rglob('*.py'))


def extract_detailed_symbols(file_path: Path, repo_path: Path) -> Dict:
    """Extract detailed symbol information including imports and relationships."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))
        
        rel_path = str(file_path.relative_to(repo_path))
        
        symbols = {
            'path': rel_path,
            'imports': [],
            'classes': [],
            'functions': [],
            'exports': [],
            'docstring': ast.get_docstring(tree) or ""
        }
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    symbols['imports'].append({
                        'module': alias.name,
                        'alias': alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    symbols['imports'].append({
                        'from': module,
                        'name': alias.name,
                        'alias': alias.asname
                    })
        
        # Extract top-level definitions
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append({
                            'name': item.name,
                            'params': [arg.arg for arg in item.args.args],
                            'is_public': not item.name.startswith('_')
                        })
                
                symbols['classes'].append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or "",
                    'methods': methods,
                    'bases': [_get_name(base) for base in node.bases],
                    'is_public': not node.name.startswith('_')
                })
                
                # Public classes are exports
                if not node.name.startswith('_'):
                    symbols['exports'].append(node.name)
            
            elif isinstance(node, ast.FunctionDef):
                symbols['functions'].append({
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or "",
                    'params': [arg.arg for arg in node.args.args],
                    'is_public': not node.name.startswith('_')
                })
                
                # Public functions are exports
                if not node.name.startswith('_'):
                    symbols['exports'].append(node.name)
        
        return symbols
    except Exception as e:
        return {
            'path': str(file_path.relative_to(repo_path)),
            'error': str(e),
            'imports': [],
            'classes': [],
            'functions': [],
            'exports': []
        }


def _get_name(node):
    """Helper to get name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    return str(node)


def categorize_files(symbols_by_file: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize files by their role in the codebase."""
    categories = {
        'entry_points': [],
        'services': [],
        'models': [],
        'utilities': [],
        'configuration': [],
        'other': []
    }
    
    for symbols in symbols_by_file:
        path = symbols['path']
        
        if '__main__' in path or 'main.py' in path or 'run.py' in path:
            categories['entry_points'].append(symbols)
        elif 'service' in path.lower():
            categories['services'].append(symbols)
        elif 'model' in path.lower():
            categories['models'].append(symbols)
        elif 'config' in path.lower() or 'settings' in path.lower():
            categories['configuration'].append(symbols)
        elif 'util' in path.lower() or 'helper' in path.lower():
            categories['utilities'].append(symbols)
        else:
            categories['other'].append(symbols)
    
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
            
            if file_symbols.get('docstring'):
                lines.append(f"> {file_symbols['docstring'][:100]}...")
            
            lines.append("")
            
            # Exports
            if file_symbols.get('exports'):
                lines.append(f"**Exports:** {', '.join(file_symbols['exports'][:5])}")
                lines.append("")
            
            # Classes
            if file_symbols.get('classes'):
                lines.append("**Classes:**")
                for cls in file_symbols['classes']:
                    public_methods = [m['name'] for m in cls['methods'] if m['is_public']]
                    if cls.get('bases'):
                        lines.append(f"- `{cls['name']}` (inherits: {', '.join(cls['bases'])})")
                    else:
                        lines.append(f"- `{cls['name']}`")
                    
                    if public_methods:
                        lines.append(f"  - Methods: {', '.join(public_methods[:5])}")
                    
                    if cls.get('docstring'):
                        lines.append(f"  - {cls['docstring'][:80]}...")
                lines.append("")
            
            # Functions
            if file_symbols.get('functions'):
                public_funcs = [f for f in file_symbols['functions'] if f['is_public']]
                if public_funcs:
                    lines.append("**Functions:**")
                    for func in public_funcs[:5]:
                        params = ', '.join(func['params'][:3])
                        lines.append(f"- `{func['name']}({params})`")
                        if func.get('docstring'):
                            lines.append(f"  - {func['docstring'][:80]}...")
                    lines.append("")
            
            # Key imports
            if file_symbols.get('imports'):
                internal_imports = [
                    imp for imp in file_symbols['imports']
                    if imp.get('from', '').startswith('src') or imp.get('module', '').startswith('src')
                ]
                if internal_imports:
                    lines.append(f"**Internal Dependencies:** {len(internal_imports)} imports")
                    lines.append("")
            
            if file_symbols.get('error'):
                lines.append(f"⚠️ _Error parsing file: {file_symbols['error']}_")
                lines.append("")
    
    return '\n'.join(lines)


def generate_sourcegraph_map(repo_path: str) -> str:
    """Generate a Sourcegraph-style repository map."""
    repo_path = Path(repo_path)
    
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


# Fix the _get_name helper to be a module-level function
import ast as _ast
def _get_name(node):
    """Helper to get name from AST node."""
    if isinstance(node, _ast.Name):
        return node.id
    elif isinstance(node, _ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    return str(node)


if __name__ == '__main__':
    repo_path = Path(__file__).parent
    map_content = generate_sourcegraph_map(repo_path)
    
    # Save to file
    output_file = repo_path / '.repo-map-sourcegraph.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(map_content)
    
    print(f"Sourcegraph-style repository map generated: {output_file}")
    print(f"\nPreview (first 50 lines):")
    print('\n'.join(map_content.split('\n')[:50]))
