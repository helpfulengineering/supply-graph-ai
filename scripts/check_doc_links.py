#!/usr/bin/env python3
"""Fail when a documentation link cannot be followed to a real page.

Three classes of rot, none of which mkdocs catches on its own:

1. **Wrong host.** `docs.openhardwaremanager.org` does not resolve; the docs are
   served at `www.openhardwaremanager.org/docs/`. The facility form pointed at
   the former for months.
2. **Absolute links into our own docs.** mkdocs validates relative links between
   pages and treats anything with a scheme as external, so a link to
   `www.openhardwaremanager.org/docs/guides/nope/` is never checked — including
   from the frontend, which is where most of them live.
3. **Repo-internal markdown links.** Cross-links between `docs/`, `deploy/` and
   the README point at files, not pages, and nothing validated them.

Resolves against the SOURCE tree rather than a built site, so the gate needs no
mkdocs run. Pages generated at build time (`reference/whats-built.md`) exist only
in the output, so nav entries count as valid targets alongside files on disk.

    python scripts/check_doc_links.py            # check
    python scripts/check_doc_links.py --list     # print every link it resolved
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs-site" / "docs"
SITE_HOSTS = {"openhardwaremanager.org", "www.openhardwaremanager.org"}
WRONG_HOSTS = {"docs.openhardwaremanager.org"}
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "docs-dist",
    ".next",
    "site",
    "artifacts",
    "storage",
}

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HREF = re.compile(r"href=[\"']([^\"']+)[\"']")


def nav_targets() -> set[str]:
    """Page paths named in mkdocs nav, which may be generated rather than on disk."""
    cfg = ROOT / "docs-site" / "mkdocs.yml"
    if not cfg.exists():
        return set()
    return {
        m.group(1).removesuffix(".md")
        for m in re.finditer(r":\s*([A-Za-z0-9_\-/]+\.md)\s*$", cfg.read_text(), re.M)
    }


def doc_pages() -> set[str]:
    pages = (
        {p.relative_to(DOCS).as_posix().removesuffix(".md") for p in DOCS.rglob("*.md")}
        if DOCS.exists()
        else set()
    )
    pages |= nav_targets()
    pages |= {"", "index"}
    return pages


def sources() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for p in ROOT.rglob("*.md"):
        if SKIP_DIRS & set(p.relative_to(ROOT).parts):
            continue
        out.append((p, p.read_text(errors="ignore")))
    for base in (ROOT / "frontend" / "src", ROOT / "frontend" / "app"):
        if not base.exists():
            continue
        for pat in ("**/*.ts", "**/*.tsx"):
            for p in base.glob(pat):
                if SKIP_DIRS & set(p.relative_to(ROOT).parts):
                    continue
                out.append((p, p.read_text(errors="ignore")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print every resolved link")
    args = ap.parse_args()

    pages = doc_pages()
    problems: list[str] = []
    checked = 0

    for f, text in sources():
        rel_f = f.relative_to(ROOT).as_posix()
        in_docs = rel_f.startswith("docs-site/docs/")
        for m in list(MD_LINK.finditer(text)) + list(HREF.finditer(text)):
            raw = m.group(1).strip()
            if (
                raw.startswith(("mailto:", "tel:", "data:", "#", "{"))
                or "${" in raw
                or "<" in raw
            ):
                continue
            line = text.count("\n", 0, m.start()) + 1
            where = f"{rel_f}:{line}"
            u = urlparse(raw)
            host = u.netloc.lower()

            if host in WRONG_HOSTS:
                problems.append(
                    f"{where}\n      {raw}\n"
                    f"      -> {host} does not serve the docs; use www.openhardwaremanager.org/docs/"
                )
                continue

            if host and host not in SITE_HOSTS:
                continue  # genuinely external; not this gate's business

            if host in SITE_HOSTS:
                path = unquote(u.path)
                if not path.startswith("/docs"):
                    continue  # an app route, not a docs link
                target = path[len("/docs") :].strip("/")
                checked += 1
                if target not in pages:
                    problems.append(
                        f"{where}\n      {raw}\n      -> no docs page {target!r}"
                    )
                continue

            if raw.startswith(("http://", "https://")):
                continue

            if in_docs:
                continue  # relative links between docs pages: mkdocs validates these

            if f.suffix != ".md":
                # A bare path in application source is a ROUTE, not a file --
                # `/settings/session` is a page the router serves. Only the two
                # checks above (wrong host, absolute docs link) apply to code.
                continue

            # repo-internal markdown link -> a real file on disk
            path = unquote(u.path)
            if not path:
                continue
            target_p = (
                (ROOT / path.lstrip("/")) if raw.startswith("/") else (f.parent / path)
            )
            target_p = Path(os.path.normpath(target_p))
            checked += 1
            if target_p.exists():
                continue
            if any(Path(f"{target_p}{ext}").exists() for ext in (".md", ".html")):
                continue
            if (target_p / "index.md").exists() or (target_p / "README.md").exists():
                continue
            problems.append(f"{where}\n      {raw}\n      -> missing file")

    if args.list:
        print(f"checked {checked} link(s) across {len(sources())} file(s)")

    if problems:
        print(f"Broken documentation links ({len(problems)}):\n", file=sys.stderr)
        for p in problems:
            print(f"  {p}\n", file=sys.stderr)
        return 1

    print(f"OK: {checked} documentation link(s) resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
