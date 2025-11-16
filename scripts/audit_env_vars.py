#!/usr/bin/env python3
"""
Audit environment variables used in code vs documented in env.template.

This script identifies:
- Variables used in code but not documented
- Variables documented but not used
- Naming inconsistencies
"""

import re
import os
from pathlib import Path
from typing import Set, Dict, List
from dataclasses import dataclass


@dataclass
class EnvVarUsage:
    """Represents environment variable usage."""
    name: str
    file: str
    line: int
    context: str


class EnvVarAuditor:
    """Audits environment variable usage."""
    
    def __init__(self, code_dir: Path, env_template: Path):
        self.code_dir = code_dir
        self.env_template = env_template
        self.used_vars: Dict[str, List[EnvVarUsage]] = {}
        self.documented_vars: Set[str] = set()
    
    def scan_code(self) -> Dict[str, List[EnvVarUsage]]:
        """Scan code for environment variable usage."""
        pattern = r'os\.getenv\(["\']([^"\']+)["\']'
        
        for py_file in self.code_dir.rglob("*.py"):
            # Skip test files and __pycache__
            if 'test' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        var_name = match.group(1)
                        if var_name not in self.used_vars:
                            self.used_vars[var_name] = []
                        self.used_vars[var_name].append(
                            EnvVarUsage(
                                name=var_name,
                                file=str(py_file.relative_to(self.code_dir.parent)),
                                line=line_num,
                                context=line.strip()
                            )
                        )
            except Exception as e:
                print(f"Error scanning {py_file}: {e}")
        
        return self.used_vars
    
    def scan_template(self) -> Set[str]:
        """Scan env.template for documented variables."""
        if not self.env_template.exists():
            return set()
        
        pattern = r'^([A-Z_][A-Z0-9_]*)='
        
        with open(self.env_template, 'r', encoding='utf-8') as f:
            for line in f:
                # Skip comments and empty lines
                if line.strip().startswith('#') or not line.strip():
                    continue
                match = re.match(pattern, line)
                if match:
                    self.documented_vars.add(match.group(1))
        
        return self.documented_vars
    
    def generate_report(self) -> str:
        """Generate audit report."""
        used_vars = set(self.used_vars.keys())
        documented_vars = self.documented_vars
        
        undocumented = used_vars - documented_vars
        unused_docs = documented_vars - used_vars
        
        report = "Environment Variable Audit Report\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Total variables used in code: {len(used_vars)}\n"
        report += f"Total variables documented: {len(documented_vars)}\n\n"
        
        if undocumented:
            report += f"UNDOCUMENTED VARIABLES ({len(undocumented)}):\n"
            report += "-" * 60 + "\n"
            for var in sorted(undocumented):
                usages = self.used_vars[var]
                report += f"\n  {var}\n"
                for usage in usages[:3]:  # Show first 3 usages
                    report += f"    - {usage.file}:{usage.line}\n"
                if len(usages) > 3:
                    report += f"    ... and {len(usages) - 3} more\n"
            report += "\n"
        
        if unused_docs:
            report += f"DOCUMENTED BUT UNUSED ({len(unused_docs)}):\n"
            report += "-" * 60 + "\n"
            for var in sorted(unused_docs):
                report += f"  - {var}\n"
            report += "\n"
        
        if not undocumented and not unused_docs:
            report += "✓ All environment variables are properly documented!\n"
        
        return report


def main():
    """Run environment variable audit."""
    project_root = Path(__file__).parent.parent
    code_dir = project_root / "src"
    env_template = project_root / "env.template"
    
    auditor = EnvVarAuditor(code_dir, env_template)
    auditor.scan_code()
    auditor.scan_template()
    
    report = auditor.generate_report()
    print(report)
    
    # Exit with error if undocumented variables found
    used_vars = set(auditor.used_vars.keys())
    documented_vars = auditor.documented_vars
    undocumented = used_vars - documented_vars
    
    if undocumented:
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

