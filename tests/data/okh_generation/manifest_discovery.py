"""Discover generated OKH manifests and normalize repo URLs / filename stems."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Set
from urllib.parse import urlparse


def canonical_repo_url(url: str) -> str:
    """Normalize a git hosting URL for join keys (host lowercased, no .git / slash)."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        # bare path-ish fallback
        cleaned = raw.rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        return cleaned.lower()
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return f"{parsed.scheme.lower()}://{host}{path}"


def title_slug_for_filename(title: str, fallback_id: str) -> str:
    """Kebab-case slug from title; fall back to dataset id when title is empty."""
    text = (title or "").strip().lower()
    if not text:
        return _slug_token(fallback_id) or "manifest"
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return slug or (_slug_token(fallback_id) or "manifest")


def allocate_unique_slug(base: str, used: Set[str]) -> str:
    """Return *base* or ``base-2``, ``base-3``, … so stems stay unique within a run."""
    stem = base or "manifest"
    if stem not in used:
        used.add(stem)
        return stem
    n = 2
    while f"{stem}-{n}" in used:
        n += 1
    unique = f"{stem}-{n}"
    used.add(unique)
    return unique


def find_generated_manifest_path(
    manifests_dir: Path,
    layer: str,
    url: str,
    dataset_id: str = "",
) -> Optional[Path]:
    """Locate ``*-{layer}.json`` for *url*, preferring legacy ``{id}-{layer}.json``."""
    directory = Path(manifests_dir)
    if not directory.is_dir():
        return None

    layer_tag = layer.strip()
    legacy = directory / f"{dataset_id}-{layer_tag}.json"
    if dataset_id and legacy.is_file():
        return legacy

    target = canonical_repo_url(url)
    for path in sorted(directory.glob(f"*-{layer_tag}.json")):
        if path.stem.endswith("-bom"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if target and canonical_repo_url(str(data.get("repo") or "")) == target:
            return path
    return None


def _slug_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
