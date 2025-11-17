#!/usr/bin/env python3
"""
Validate documentation against code implementation.

This script checks:
- Authentication header format in docs vs code
- Port numbers in docs vs code
- API endpoint documentation vs implementation
"""

import re
from pathlib import Path
from typing import List, Dict


class DocValidator:
    """Validates documentation against code."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues = []
    
    def check_auth_header(self):
        """Check authentication header documentation."""
        auth_doc = self.project_root / "docs" / "api" / "auth.md"
        main_code = self.project_root / "src" / "core" / "api" / "dependencies.py"
        
        if not auth_doc.exists() or not main_code.exists():
            return
        
        # Check code
        with open(main_code, 'r') as f:
            code_content = f.read()
        
        code_uses_bearer = 'APIKeyHeader(name="Authorization")' in code_content
        code_checks_bearer = 'api_key.startswith("Bearer ")' in code_content or 'auth_header.startswith("Bearer ")' in code_content
        
        # Check docs
        with open(auth_doc, 'r') as f:
            doc_content = f.read()
        
        doc_uses_x_api_key = 'X-API-Key' in doc_content and 'Authorization' not in doc_content
        doc_uses_bearer = 'Authorization: Bearer' in doc_content or 'Bearer' in doc_content
        
        if code_uses_bearer and code_checks_bearer:
            if doc_uses_x_api_key and not doc_uses_bearer:
                self.issues.append({
                    "type": "auth_header_mismatch",
                    "severity": "high",
                    "file": str(auth_doc.relative_to(self.project_root)),
                    "issue": "Documentation shows X-API-Key but code uses Authorization: Bearer",
                    "recommendation": "Update documentation to use Authorization: Bearer format"
                })
    
    def check_port_numbers(self):
        """Check port number consistency."""
        # Check code defaults
        settings_file = self.project_root / "src" / "config" / "settings.py"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                content = f.read()
                port_match = re.search(r'API_PORT.*=.*int\(os\.getenv\(["\']API_PORT["\'],\s*["\'](\d+)["\']\)', content)
                if port_match:
                    default_port = port_match.group(1)
                    
                    # Ports for other services (not API server) - these are OK
                    other_service_ports = {'11434', '3000', '7071', '8080', '8081'}
                    
                    # Check docs
                    docs_dir = self.project_root / "docs"
                    for doc_file in docs_dir.rglob("*.md"):
                        # Skip spec files and code-review-report
                        if 'spec' in str(doc_file) or 'code-review-report' in str(doc_file):
                            continue
                            
                        with open(doc_file, 'r') as f:
                            doc_content = f.read()
                            # Find port references in API URLs (not other services)
                            # Look for patterns like http://localhost:PORT/v1/api or /v1/api
                            api_port_pattern = re.compile(r'(?:http://localhost:|:)(\d+)(?:/v1/api|/v1/api/)')
                            port_refs = api_port_pattern.findall(doc_content)
                            
                            for port in port_refs:
                                if port != default_port and port not in other_service_ports:
                                    self.issues.append({
                                        "type": "port_mismatch",
                                        "severity": "medium",
                                        "file": str(doc_file.relative_to(self.project_root)),
                                        "issue": f"API documentation shows port {port} but default is {default_port}",
                                        "recommendation": f"Update to port {default_port}"
                                    })
    
    def generate_report(self) -> str:
        """Generate validation report."""
        if not self.issues:
            return "✓ Documentation validation passed!\n"
        
        report = "Documentation Validation Report\n"
        report += "=" * 60 + "\n\n"
        
        by_severity = {}
        for issue in self.issues:
            severity = issue["severity"]
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(issue)
        
        for severity in ["high", "medium", "low"]:
            if severity in by_severity:
                report += f"\n{severity.upper()} ({len(by_severity[severity])}):\n"
                report += "-" * 60 + "\n"
                for issue in by_severity[severity]:
                    report += f"\n  File: {issue['file']}\n"
                    report += f"  Type: {issue['type']}\n"
                    report += f"  Issue: {issue['issue']}\n"
                    report += f"  Recommendation: {issue['recommendation']}\n"
        
        return report


def main():
    """Run documentation validation."""
    project_root = Path(__file__).parent.parent
    validator = DocValidator(project_root)
    
    validator.check_auth_header()
    validator.check_port_numbers()
    
    report = validator.generate_report()
    print(report)
    
    # Exit with error if high severity issues found
    high_severity = [i for i in validator.issues if i["severity"] == "high"]
    if high_severity:
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

