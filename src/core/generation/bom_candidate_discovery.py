"""
Ranked BOM file path discovery from repository file listings.

Only paths that appear in :class:`ProjectData.files` are returned — no invented
GitHub paths. Used by the LLM context, :class:`BOMCollector`, and shared
``find_bom_files`` helpers to avoid duplicate, inconsistent heuristics.

See ``tests/unit/test_bom_candidate_discovery.py`` and docs in the generation
architecture notes.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .models import FileInfo, ProjectData

logger = logging.getLogger(__name__)


class BomCandidateKind(str, Enum):
    """How the path was matched as a BOM candidate."""

    DEDICATED_BASENAME = "dedicated_basename"
    STEM_UNDERSCORE_BOM = "stem_underscore_bom"
    STEM_HYPHEN_BOM = "stem_hyphen_bom"
    PARTS_LIST_FILE = "parts_list_file"
    MATERIALS_LIST_FILE = "materials_list_file"


# (regex on normalized repo-relative path, confidence, kind)
# Higher score = more specific / less ambiguous BOM filename.
_BOM_PATH_RULES: Tuple[Tuple[str, float, BomCandidateKind], ...] = (
    (
        r"(?i)(^|/)bill_of_materials(\.(csv|txt|md|json|yaml|yml))?$",
        0.94,
        BomCandidateKind.DEDICATED_BASENAME,
    ),
    (
        r"(?i)(^|/)bom(\.(csv|txt|md|json|yaml|yml))?$",
        0.93,
        BomCandidateKind.DEDICATED_BASENAME,
    ),
    (
        r"(?i)(^|/)[^/]+_bom\.(csv|tsv|txt)$",
        0.91,
        BomCandidateKind.STEM_UNDERSCORE_BOM,
    ),
    (
        r"(?i)(^|/)[^/]+-bom\.(csv|tsv|txt|json)$",
        0.91,
        BomCandidateKind.STEM_HYPHEN_BOM,
    ),
    (
        r"(?i)(^|/)parts(\.(csv|txt|md|json|yaml|yml))?$",
        0.78,
        BomCandidateKind.PARTS_LIST_FILE,
    ),
    (
        r"(?i)(^|/)materials(\.(csv|txt|md|json|yaml|yml))?$",
        0.76,
        BomCandidateKind.MATERIALS_LIST_FILE,
    ),
)


def _normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def score_bom_path(path: str) -> Optional[Tuple[float, BomCandidateKind]]:
    """
    Return (confidence, kind) if ``path`` looks like a dedicated BOM file, else None.

    Patterns apply to the full repo-relative path (slashes preserved) so nested
    files such as ``hardware/bom.csv`` match.
    """
    norm = _normalize_rel_path(path)
    if not norm:
        return None
    best: Optional[Tuple[float, BomCandidateKind]] = None
    for pattern, conf, kind in _BOM_PATH_RULES:
        if re.search(pattern, norm):
            if best is None or conf > best[0]:
                best = (conf, kind)
    return best


def path_matches_dedicated_bom_file(path: str) -> bool:
    """True if ``path`` matches any BOM file naming rule (BOMCollector gate)."""
    return score_bom_path(path) is not None


@dataclass(frozen=True)
class BomCandidate:
    """A repository file path that may hold BOM tabular or structured data."""

    path: str
    kind: BomCandidateKind
    confidence: float
    exists_in_tree: bool = True


def list_bom_candidate_paths_from_files(files: List[FileInfo]) -> List[str]:
    """Return unique BOM-like paths, highest confidence first."""
    candidates = _candidates_from_files(files)
    return [c.path for c in candidates]


def list_bom_candidates(project_data: ProjectData) -> List[BomCandidate]:
    """Ranked BOM candidates from ``project_data.files`` only."""
    return _candidates_from_files(project_data.files)


def _candidates_from_files(files: List[FileInfo]) -> List[BomCandidate]:
    scored: List[Tuple[float, str, BomCandidate]] = []
    seen: set[str] = set()
    for fi in files:
        path = fi.path
        if path in seen:
            continue
        hit = score_bom_path(path)
        if not hit:
            continue
        conf, kind = hit
        scored.append((conf, path, BomCandidate(path=path, kind=kind, confidence=conf)))
        seen.add(path)
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [t[2] for t in scored]


def _norm_rel_path_for_compare(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("./")


def _expand_norm_set(paths: frozenset[str]) -> frozenset[str]:
    out: set[str] = set(paths)
    for p in paths:
        out.add(_norm_rel_path_for_compare(p))
    return frozenset(out)


def _allowed_path_set(files: List[FileInfo]) -> frozenset[str]:
    raw = list_bom_candidate_paths_from_files(files)
    out: set[str] = set()
    for p in raw:
        out.add(p)
        out.add(_norm_rel_path_for_compare(p))
    return frozenset(out)


def repo_relative_bom_path_allowed(path: str, allowed: frozenset[str]) -> bool:
    """
    True if ``path`` may be used as a repo-relative BOM reference for packaging.

    HTTP(S) URLs are always allowed. Otherwise ``path`` must match a ranked BOM
    candidate path from the extracted file tree (case-sensitive path match after
    slash normalization).
    """
    p = path.strip()
    if not p:
        return False
    if p.startswith(("http://", "https://")):
        return True
    n = _norm_rel_path_for_compare(p)
    if n in allowed:
        return True
    if p in allowed:
        return True
    return False


def _effective_bom_path_allowset(project_data: ProjectData) -> frozenset[str]:
    """
    Paths that may appear as repo-relative ``bom`` / ``bom.external_file``.

    Starts from ranked tree candidates. When ``project_data.metadata`` contains
    ``_bom_http_verify_summary`` with ``applied: True`` (GitHub raw checks ran),
    intersect with ``_bom_http_allowed_paths`` so only HTTP-confirmed paths remain.
    """
    tree = _allowed_path_set(project_data.files)
    meta = project_data.metadata or {}
    summary = meta.get("_bom_http_verify_summary")
    if not isinstance(summary, dict) or not summary.get("applied"):
        return tree
    http_paths = meta.get("_bom_http_allowed_paths")
    if not isinstance(http_paths, frozenset):
        return tree
    expanded = _expand_norm_set(http_paths)
    return tree & expanded


def sanitize_bom_field_for_manifest(bom_value: Any, project_data: ProjectData) -> Any:
    """
    Strip unverified repo-relative BOM paths before OKH export.

    LLM or legacy layers may set ``bom`` to a string path or ``bom.external_file``
    to a path that does not exist in ``project_data.files``. That breaks package
    builds (404 on raw GitHub). URLs are kept; unknown repo paths are removed.

    When HTTP verification has run (see :mod:`bom_http_verify`), repo-relative paths
    must also pass the raw GitHub probe (404s dropped).
    """
    allowed = _effective_bom_path_allowset(project_data)

    if isinstance(bom_value, str):
        s = bom_value.strip()
        if not s:
            return ""
        if repo_relative_bom_path_allowed(s, allowed):
            return bom_value
        logger.info("Removing unverified BOM string path from manifest: %r", bom_value)
        return ""

    if isinstance(bom_value, dict):
        out = dict(bom_value)
        ext = out.get("external_file")
        if isinstance(ext, str) and ext.strip():
            if not repo_relative_bom_path_allowed(ext.strip(), allowed):
                logger.info(
                    "Clearing unverified bom.external_file from manifest: %r", ext
                )
                out["external_file"] = None
        return out

    return bom_value


def build_bom_discovery_metadata(project_data: ProjectData) -> Dict[str, Any]:
    """Structured BOM path discovery summary for ``manifest.metadata.bom_discovery``."""
    cands = _candidates_from_files(project_data.files)
    out: Dict[str, Any] = {
        "candidates_ranked": [c.path for c in cands[:25]],
        "candidate_count": len(cands),
        "top_confidence": round(cands[0].confidence, 4) if cands else None,
        "policy_version": 3,
    }
    summary = (project_data.metadata or {}).get("_bom_http_verify_summary")
    if isinstance(summary, dict) and summary.get("applied"):
        out["http_verify"] = summary
    return out
