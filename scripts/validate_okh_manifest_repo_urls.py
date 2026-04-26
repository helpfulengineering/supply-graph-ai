#!/usr/bin/env python3
"""
Probe OKH manifest repository-relative paths against GitHub raw URLs.

Resolves ``https://github.com/owner/repo`` + relative path using the repo's
*default branch* (same logic as package build). Issues HTTP HEAD requests and
reports status codes so you can see mismatches (wrong path, wrong branch, etc.).

Examples
--------
    conda activate supply-graph-ai
    python scripts/validate_okh_manifest_repo_urls.py tmp/oshwa/okh-manifests/beaglebone-black-4L.json
    python scripts/validate_okh_manifest_repo_urls.py tmp/oshwa/okh-manifests/beaglebone-black-4L.json --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _string_paths(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item)
        return out
    return []


def collect_relative_paths(manifest: Any) -> List[Tuple[str, str]]:
    """Return (label, repo_relative_path) for paths the builder would map to raw GitHub."""
    rows: List[Tuple[str, str]] = []

    def add_docs(label: str, docs: Any) -> None:
        if not docs:
            return
        for i, doc in enumerate(docs):
            path = getattr(doc, "path", None) or (
                doc.get("path") if isinstance(doc, dict) else None
            )
            if not path or path.startswith(("http://", "https://")):
                continue
            rows.append((f"{label}[{i}]", path))

    add_docs("design_files", manifest.design_files)
    add_docs("manufacturing_files", manifest.manufacturing_files)
    add_docs("making_instructions", manifest.making_instructions)
    add_docs("operating_instructions", manifest.operating_instructions)
    add_docs("technical_specifications", manifest.technical_specifications)
    add_docs("publications", manifest.publications)

    for attr in (
        "image",
        "readme",
        "archive_download",
        "documentation_home",
        "contribution_guide",
    ):
        v = getattr(manifest, attr, None)
        if (
            isinstance(v, str)
            and v.strip()
            and not v.startswith(("http://", "https://"))
        ):
            rows.append((attr, v))

    bom = getattr(manifest, "bom", None)
    if isinstance(bom, dict):
        ext = bom.get("external_file")
        if (
            isinstance(ext, str)
            and ext.strip()
            and not ext.startswith(("http://", "https://"))
        ):
            rows.append(("bom.external_file", ext))
    elif (
        isinstance(bom, str)
        and bom.strip()
        and not bom.startswith(("http://", "https://"))
    ):
        rows.append(("bom", bom))

    parts = getattr(manifest, "parts", None) or []
    for i, part in enumerate(parts):
        for field in ("source", "export", "auxiliary"):
            for p in _string_paths(getattr(part, field, None)):
                if not p.startswith(("http://", "https://")):
                    rows.append((f"parts[{i}].{field}", p))
        img = getattr(part, "image", None)
        if (
            isinstance(img, str)
            and img.strip()
            and not img.startswith(("http://", "https://"))
        ):
            rows.append((f"parts[{i}].image", img))

    return rows


async def _probe(
    manifest_path: Path,
) -> Tuple[str, List[Dict[str, Any]]]:
    import aiohttp

    from src.core.models.okh import OKHManifest
    from src.core.packaging.github_raw_urls import github_raw_file_url

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = OKHManifest.from_dict(data)
    repo = manifest.repo
    if not repo or "github.com" not in repo:
        raise SystemExit("Manifest has no github.com repo URL; nothing to probe.")

    rel_rows = collect_relative_paths(manifest)
    results: List[Dict[str, Any]] = []

    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"User-Agent": "supply-graph-ai-validate-manifest-urls/1.0"}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        for label, rel_path in rel_rows:
            try:
                url = github_raw_file_url(repo, rel_path)
            except ValueError as e:
                results.append(
                    {
                        "label": label,
                        "relative_path": rel_path,
                        "url": None,
                        "status": None,
                        "ok": False,
                        "error": str(e),
                    }
                )
                continue

            status: Any = None
            err: Any = None
            try:
                async with session.head(url, allow_redirects=True) as resp:
                    status = resp.status
            except Exception as e:
                err = str(e)

            ok = status == 200 if isinstance(status, int) else False
            results.append(
                {
                    "label": label,
                    "relative_path": rel_path,
                    "url": url,
                    "status": status,
                    "ok": ok,
                    "error": err,
                }
            )

    return repo, results


async def _run_async(args: argparse.Namespace) -> int:
    manifest_path = args.manifest.expanduser().resolve()
    if not manifest_path.is_file():
        print(f"File not found: {manifest_path}", file=sys.stderr)
        return 1

    repo, results = await _probe(manifest_path)
    bad = [r for r in results if not r.get("ok")]

    if args.json:
        print(
            json.dumps(
                {"repo": repo, "manifest": manifest_path.name, "results": results},
                indent=2,
            )
        )
    else:
        print(f"Repo: {repo}")
        print(f"Paths checked: {len(results)}")
        for r in results:
            st = r.get("status")
            flag = "OK" if r.get("ok") else "!!"
            print(
                f"  [{flag}] {r['label']}: {r['relative_path']}\n"
                f"       -> {r.get('url')}\n"
                f"       status={st} {r.get('error') or ''}"
            )
        print()
        if bad:
            print(f"{len(bad)} path(s) missing or failed (see !! above).")
        else:
            print("All probed URLs returned HTTP 200.")

    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to OKH JSON manifest",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable report",
    )
    args = parser.parse_args()
    return asyncio.run(_run_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
