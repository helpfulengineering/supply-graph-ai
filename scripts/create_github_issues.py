#!/usr/bin/env python3
"""
Create GitHub issues from the structured markdown issue definitions in
notes/github-issues.md.

Usage:
    # Dry-run (default): preview all parsed issues without creating anything
    python scripts/create_github_issues.py

    # Dry-run with verbose body output
    python scripts/create_github_issues.py --verbose

    # Create all issues (requires confirmation)
    python scripts/create_github_issues.py --create

    # Create only the first 5 issues
    python scripts/create_github_issues.py --create --limit 5

    # Create issues from a specific phase only
    python scripts/create_github_issues.py --create --phase 1

    # Create a single issue by ID
    python scripts/create_github_issues.py --create --issue-id 1.1.1

    # Skip confirmation prompt (for CI/automation)
    python scripts/create_github_issues.py --create --yes

    # Specify a custom repo (default: auto-detected from git remote)
    python scripts/create_github_issues.py --create --repo owner/repo

Prerequisites:
    - GitHub CLI (gh) installed: https://cli.github.com/
    - Authenticated: gh auth login
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ParsedIssue:
    """A single parsed issue from the markdown document."""

    issue_id: str  # e.g. "1.1.1"
    heading: str  # e.g. "Define Canonical Test Workflows for Design-to-Manufacturing"
    title: str  # The **Title** field value
    labels: List[str]  # Parsed from **Labels** field
    description: str  # The **Description** block
    acceptance_criteria: str  # The **Acceptance Criteria** block
    dependencies: str  # The **Dependencies** block
    estimated_effort: str  # The **Estimated Effort** value
    technical_notes: str  # The **Technical Notes** block
    phase: int = 0  # Extracted from issue_id (first digit)

    def __post_init__(self):
        self.phase = int(self.issue_id.split(".")[0])

    def build_body(self) -> str:
        """Build the full GitHub issue body from structured fields."""
        parts = []

        if self.description.strip():
            parts.append(self.description.strip())

        if self.acceptance_criteria.strip():
            parts.append("## Acceptance Criteria\n")
            parts.append(self.acceptance_criteria.strip())

        if self.dependencies.strip() and self.dependencies.strip().lower() not in (
            "none",
            "- none",
            "none (foundational issue)",
            "- none (foundational issue)",
        ):
            parts.append("## Dependencies\n")
            parts.append(self.dependencies.strip())

        if self.estimated_effort.strip():
            parts.append(f"## Estimated Effort\n\n{self.estimated_effort.strip()}")

        if self.technical_notes.strip():
            parts.append("## Technical Notes\n")
            parts.append(self.technical_notes.strip())

        # Add a footer linking back to the source document
        parts.append(
            "---\n"
            f"*Generated from `notes/github-issues.md` — Issue {self.issue_id}*"
        )

        return "\n\n".join(parts)

    def summary(self, verbose: bool = False) -> str:
        """Return a human-readable summary for dry-run output."""
        labels_str = ", ".join(self.labels) if self.labels else "(none)"
        lines = [
            f"  Issue ID:  {self.issue_id}",
            f"  Title:     {self.title}",
            f"  Labels:    {labels_str}",
            f"  Effort:    {self.estimated_effort}",
        ]
        if verbose:
            body = self.build_body()
            # Show first 500 chars of body
            preview = body[:500] + ("..." if len(body) > 500 else "")
            lines.append(f"  Body preview:\n{_indent(preview, 13)}")
        return "\n".join(lines)


def _indent(text: str, spaces: int) -> str:
    """Indent every line of text by the given number of spaces."""
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.splitlines())


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

# Pattern matching the issue heading line:
#   ### Issue 1.1.1: Define Canonical Test Workflows ...
ISSUE_HEADING_RE = re.compile(
    r"^### Issue (\d+\.\d+\.\d+):\s*(.+)$", re.MULTILINE
)

# Pattern for the **Title** field value
TITLE_RE = re.compile(r"^\*\*Title\*\*:\s*(.+)$", re.MULTILINE)

# Pattern for the **Labels** field — extracts backtick-enclosed labels
LABELS_RE = re.compile(r"`([^`]+)`")


def parse_issues(markdown_text: str) -> List[ParsedIssue]:
    """Parse all issues from the markdown document."""
    issues: List[ParsedIssue] = []

    # Split document at each issue heading
    heading_matches = list(ISSUE_HEADING_RE.finditer(markdown_text))

    for idx, match in enumerate(heading_matches):
        issue_id = match.group(1)
        heading = match.group(2).strip()

        # Extract the block of text for this issue (up to next issue heading or EOF)
        start = match.end()
        end = heading_matches[idx + 1].start() if idx + 1 < len(heading_matches) else len(markdown_text)
        block = markdown_text[start:end]

        # --- Parse individual fields ---

        # Title
        title_match = TITLE_RE.search(block)
        title = title_match.group(1).strip() if title_match else heading

        # Labels
        labels_line = _extract_field_line(block, "Labels")
        labels = LABELS_RE.findall(labels_line) if labels_line else []

        # Sections that span multiple lines until the next **Field** marker
        description = _extract_section(block, "Description")
        acceptance_criteria = _extract_section(block, "Acceptance Criteria")
        dependencies = _extract_section(block, "Dependencies")
        technical_notes = _extract_section(block, "Technical Notes")

        # Single-line field
        effort_line = _extract_field_line(block, "Estimated Effort")
        estimated_effort = effort_line if effort_line else ""

        issues.append(
            ParsedIssue(
                issue_id=issue_id,
                heading=heading,
                title=title,
                labels=labels,
                description=description,
                acceptance_criteria=acceptance_criteria,
                dependencies=dependencies,
                estimated_effort=estimated_effort,
                technical_notes=technical_notes,
            )
        )

    return issues


def _extract_field_line(block: str, field_name: str) -> str:
    """Extract the single-line value after **FieldName**: ..."""
    pattern = re.compile(
        rf"^\*\*{re.escape(field_name)}\*\*:\s*(.+)$", re.MULTILINE
    )
    m = pattern.search(block)
    return m.group(1).strip() if m else ""


def _extract_section(block: str, section_name: str) -> str:
    """
    Extract a multi-line section that starts with **SectionName**:
    and ends at the next **FieldName** marker, a horizontal rule (---),
    or the next issue heading.
    """
    # Find the start of this section
    pattern = re.compile(
        rf"^\*\*{re.escape(section_name)}\*\*:\s*\n?", re.MULTILINE
    )
    m = pattern.search(block)
    if not m:
        return ""

    start = m.end()

    # Find the end: next bold field marker or horizontal rule
    end_pattern = re.compile(r"^\*\*[A-Z][^*]+\*\*:|^---\s*$", re.MULTILINE)
    end_match = end_pattern.search(block, start)
    end = end_match.start() if end_match else len(block)

    return block[start:end].strip()


# ---------------------------------------------------------------------------
# GitHub CLI integration
# ---------------------------------------------------------------------------


def check_gh_cli() -> bool:
    """Check that the gh CLI is installed and authenticated."""
    if not shutil.which("gh"):
        print("ERROR: GitHub CLI (gh) is not installed.")
        print("  Install: https://cli.github.com/")
        print("  macOS:   brew install gh")
        return False

    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: GitHub CLI is not authenticated.")
        print("  Run: gh auth login")
        print(f"  Details: {result.stderr.strip()}")
        return False

    return True


def detect_repo() -> Optional[str]:
    """Detect the GitHub owner/repo from the git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        # Handle SSH: git@github.com:owner/repo.git
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    except subprocess.CalledProcessError:
        pass
    return None


def get_existing_labels(repo: str) -> set:
    """Fetch the set of label names that already exist on the repo."""
    try:
        result = subprocess.run(
            ["gh", "label", "list", "--repo", repo, "--limit", "200", "--json", "name"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            labels_data = json.loads(result.stdout)
            return {item["name"] for item in labels_data}
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return set()


def ensure_labels_exist(labels: set, repo: str) -> tuple:
    """
    Create any labels that don't already exist on the repo.
    Returns (created_count, failed_count).
    """
    existing = get_existing_labels(repo)
    missing = labels - existing

    if not missing:
        return 0, 0

    print(f"Creating {len(missing)} missing label(s) on {repo}...")

    created = 0
    failed = 0
    for label in sorted(missing):
        result = subprocess.run(
            ["gh", "label", "create", label, "--repo", repo, "--force"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            print(f"  ✓ Label created: {label}")
            created += 1
        else:
            print(f"  ✗ Failed to create label: {label} — {result.stderr.strip()}")
            failed += 1

    return created, failed


def create_issue(
    issue: ParsedIssue,
    repo: str,
    dry_run: bool = True,
    skip_labels: bool = False,
) -> Optional[str]:
    """
    Create a single GitHub issue using the gh CLI.

    Returns the URL of the created issue, or None on failure/dry-run.
    """
    if dry_run:
        return None

    cmd = [
        "gh", "issue", "create",
        "--repo", repo,
        "--title", issue.title,
        "--body", issue.build_body(),
    ]

    # Add labels (gh accepts multiple --label flags)
    if not skip_labels:
        for label in issue.labels:
            cmd.extend(["--label", label])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            return url
        else:
            print(f"  ERROR creating issue {issue.issue_id}: {result.stderr.strip()}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT creating issue {issue.issue_id}")
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Create GitHub issues from notes/github-issues.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Actually create issues (default is dry-run mode)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt (use with --create)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of issues to create",
    )
    parser.add_argument(
        "--phase",
        type=int,
        default=None,
        help="Only include issues from this phase (1-5)",
    )
    parser.add_argument(
        "--issue-id",
        type=str,
        default=None,
        help="Create a single issue by ID (e.g. 1.1.1)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="GitHub repo (owner/repo). Default: auto-detected from git remote",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show body preview in dry-run output",
    )
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="Skip applying labels to issues (create issues without labels)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to the markdown file (default: notes/github-issues.md)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between issue creation to avoid rate limits (default: 1.0)",
    )

    args = parser.parse_args()

    # Resolve input file
    if args.input:
        input_path = Path(args.input)
    else:
        # Assume running from repo root
        input_path = Path(__file__).resolve().parent.parent / "notes" / "github-issues.md"

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    # Parse the markdown
    print(f"Parsing issues from: {input_path}")
    markdown_text = input_path.read_text(encoding="utf-8")
    all_issues = parse_issues(markdown_text)
    print(f"Found {len(all_issues)} issues total.\n")

    if not all_issues:
        print("No issues found. Check the markdown format.")
        sys.exit(1)

    # Apply filters
    issues = all_issues

    if args.phase is not None:
        issues = [i for i in issues if i.phase == args.phase]
        print(f"Filtered to phase {args.phase}: {len(issues)} issues\n")

    if args.issue_id is not None:
        issues = [i for i in issues if i.issue_id == args.issue_id]
        if not issues:
            print(f"ERROR: No issue found with ID '{args.issue_id}'")
            print("Available IDs:", ", ".join(i.issue_id for i in all_issues))
            sys.exit(1)

    if args.limit is not None:
        issues = issues[: args.limit]
        print(f"Limited to first {args.limit} issue(s)\n")

    # Dry-run mode (default)
    if not args.create:
        print("=" * 60)
        print("DRY RUN — No issues will be created.")
        print("Pass --create to actually create issues on GitHub.")
        print("=" * 60)
        print()

        for idx, issue in enumerate(issues, 1):
            print(f"[{idx}/{len(issues)}]")
            print(issue.summary(verbose=args.verbose))
            print()

        print(f"Total: {len(issues)} issue(s) would be created.")
        return

    # --- Create mode ---

    # Pre-flight checks
    if not check_gh_cli():
        sys.exit(1)

    repo = args.repo or detect_repo()
    if not repo:
        print("ERROR: Could not detect GitHub repository.")
        print("  Specify with --repo owner/repo")
        sys.exit(1)

    print(f"Target repository: {repo}")
    print(f"Issues to create:  {len(issues)}")
    print()

    # Show summary before creating
    for idx, issue in enumerate(issues, 1):
        print(f"  [{idx}] {issue.issue_id}: {issue.title}")
        labels_str = ", ".join(issue.labels) if issue.labels else "(none)"
        print(f"      Labels: {labels_str}")
    print()

    # Ensure all required labels exist on the repo
    if not args.no_labels:
        all_labels = set()
        for issue in issues:
            all_labels.update(issue.labels)
        if all_labels:
            print(f"Checking {len(all_labels)} unique label(s)...")
            label_created, label_failed = ensure_labels_exist(all_labels, repo)
            if label_failed:
                print(f"\nWARNING: {label_failed} label(s) could not be created.")
                print("Use --no-labels to create issues without labels.\n")
            elif label_created:
                print(f"  {label_created} new label(s) created.\n")
            else:
                print("  All labels already exist.\n")

    # Confirmation
    if not args.yes:
        print(f"About to create {len(issues)} issue(s) in {repo}.")
        response = input("Continue? [y/N] ").strip().lower()
        if response not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    # Create issues
    print()
    created = 0
    failed = 0
    results = []

    for idx, issue in enumerate(issues, 1):
        print(f"[{idx}/{len(issues)}] Creating: {issue.issue_id} — {issue.title}...")
        url = create_issue(issue, repo, dry_run=False, skip_labels=args.no_labels)

        if url:
            print(f"  ✓ Created: {url}")
            created += 1
            results.append({"issue_id": issue.issue_id, "url": url, "title": issue.title})
        else:
            print(f"  ✗ Failed: {issue.issue_id}")
            failed += 1
            results.append({"issue_id": issue.issue_id, "url": None, "title": issue.title})

        # Rate-limit delay (skip after last issue)
        if idx < len(issues) and args.delay > 0:
            time.sleep(args.delay)

    # Summary
    print()
    print("=" * 60)
    print(f"Done! Created: {created}, Failed: {failed}, Total: {len(issues)}")
    print("=" * 60)

    # Write results to a JSON log file
    log_path = input_path.parent / "github-issues-created.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "repo": repo,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "total": len(issues),
                "created": created,
                "failed": failed,
                "issues": results,
            },
            f,
            indent=2,
        )
    print(f"Results log written to: {log_path}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
