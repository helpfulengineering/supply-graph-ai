"""
Infer OKH manufacturing_processes from file types and title/keywords.

Lives in ``src/core/generation/services/`` (pipeline helper, peer to
``FileCategorizationService``). Callers: heuristic layer, GenerationEngine
safety net, ``OKHService.backfill_manufacturing_processes`` /
``ohm okh infer-processes``. Uses taxonomy for display names; extension map
is local (conservative).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Dict, Iterable, List, Optional, Sequence

from src.core.taxonomy import taxonomy

# Extension → canonical process id. Conservative maker/OH defaults.
EXTENSION_TO_PROCESS: Dict[str, str] = {
    ".stl": "3d_printing",
    ".3mf": "3d_printing",
    ".amf": "3d_printing",
    ".obj": "3d_printing",
    ".ply": "3d_printing",
    ".gcode": "3d_printing",
    ".bgcode": "3d_printing",
    ".nc": "cnc_machining",
    ".ngc": "cnc_machining",
    ".tap": "cnc_machining",
    ".cnc": "cnc_machining",
    ".gbr": "pcb_fabrication",
    ".ger": "pcb_fabrication",
    ".drl": "pcb_fabrication",
    ".xln": "pcb_fabrication",
    ".kicad_pcb": "pcb_fabrication",
}

TEXT_PHRASES: tuple[str, ...] = (
    "3d printing",
    "3d printed",
    "3d-printed",
    "3d print",
    "3d-print",
    "additive manufacturing",
    "laser cutting",
    "laser cut",
    "laser-cut",
    "cnc machining",
    "cnc milling",
    "cnc turning",
    "pcb fabrication",
    "pcb assembly",
    "injection mold",
    "injection mould",
)

SHORT_TOKEN_TO_PROCESS: Dict[str, str] = {
    "3dp": "3d_printing",
    "fdm": "3d_printing",
    "fff": "3d_printing",
    "sla": "3d_printing",
    "sls": "3d_printing",
    "dlp": "3d_printing",
    "cnc": "cnc_machining",
    "pcb": "pcb_fabrication",
}

_TEXT_TOKEN_BLOCKLIST = frozenset(
    {
        "print",
        "printing",
        "am",
        "mold",
        "mill",
        "test",
        "testing",
        "surface",
        "finish",
        "finishing",
        "coat",
        "coating",
        "sand",
        "sanding",
        "polish",
        "polishing",
        "paint",
        "painting",
    }
)

DEFAULT_FILE_TYPE_CONFIDENCE = 0.85
DEFAULT_TEXT_CONFIDENCE = 0.72

_TOKEN_SPLIT = re.compile(r"[^a-zA-Z0-9]+")


@dataclass
class ProcessInferenceResult:
    processes: List[str] = field(default_factory=list)
    evidence: Dict[str, List[str]] = field(default_factory=dict)
    confidence: float = 0.0
    applied: bool = False


class ProcessInferenceService:
    """File-type + title/keyword → manufacturing process inference."""

    def __init__(self) -> None:
        self.extension_map = dict(EXTENSION_TO_PROCESS)
        self.confidence = DEFAULT_FILE_TYPE_CONFIDENCE
        self.text_confidence = DEFAULT_TEXT_CONFIDENCE

    def infer_from_paths(self, paths: Iterable[str]) -> ProcessInferenceResult:
        seen_ids: Dict[str, List[str]] = {}
        for raw in paths:
            if not raw or not isinstance(raw, str):
                continue
            ext = self._extension_of(raw)
            process_id = self.extension_map.get(ext) if ext else None
            if process_id is None:
                continue
            evidence_token = f"{ext} ← {raw}"
            bucket = seen_ids.setdefault(process_id, [])
            if evidence_token not in bucket:
                bucket.append(evidence_token)
        return self._result_from_ids(seen_ids, self.confidence)

    def infer_from_text(
        self,
        text: str = "",
        *,
        keywords: Optional[Sequence[str]] = None,
    ) -> ProcessInferenceResult:
        parts = [text] if text and isinstance(text, str) else []
        parts.extend(str(kw) for kw in (keywords or ()) if kw and isinstance(kw, str))
        if not parts:
            return ProcessInferenceResult()

        combined = " ".join(parts)
        combined_lower = combined.lower()
        seen_ids: Dict[str, List[str]] = {}

        for phrase in TEXT_PHRASES:
            if phrase not in combined_lower:
                continue
            canonical = taxonomy.normalize(phrase)
            if canonical is None:
                continue
            evidence = f"phrase:{phrase}"
            bucket = seen_ids.setdefault(canonical, [])
            if evidence not in bucket:
                bucket.append(evidence)

        for token in _TOKEN_SPLIT.split(combined):
            if not token:
                continue
            key = token.lower()
            if key in SHORT_TOKEN_TO_PROCESS:
                process_id: Optional[str] = SHORT_TOKEN_TO_PROCESS[key]
            elif key in _TEXT_TOKEN_BLOCKLIST or len(key) < 4:
                continue
            else:
                process_id = self._exact_taxonomy_alias(key)
            if process_id is None:
                continue
            evidence = f"token:{token}"
            bucket = seen_ids.setdefault(process_id, [])
            if evidence not in bucket:
                bucket.append(evidence)

        return self._result_from_ids(seen_ids, self.text_confidence)

    def infer(
        self,
        *,
        paths: Optional[Iterable[str]] = None,
        text: str = "",
        keywords: Optional[Sequence[str]] = None,
    ) -> ProcessInferenceResult:
        return self._merge_results(
            self.infer_from_paths(paths or ()),
            self.infer_from_text(text, keywords=keywords),
        )

    def infer_from_manifest(self, manifest: object) -> ProcessInferenceResult:
        paths = self._paths_from_manifest(manifest)
        title = getattr(manifest, "title", None) or ""
        keywords = getattr(manifest, "keywords", None) or []
        if isinstance(keywords, str):
            keywords = [keywords]
        return self.infer(paths=paths, text=str(title), keywords=list(keywords))

    def apply_to_manifest(
        self,
        manifest: object,
        *,
        only_if_empty: bool = True,
    ) -> ProcessInferenceResult:
        existing = list(getattr(manifest, "manufacturing_processes", None) or [])
        if only_if_empty and existing:
            return ProcessInferenceResult(processes=[], applied=False)

        inferred = self.infer_from_manifest(manifest)
        if not inferred.processes:
            return inferred

        if only_if_empty:
            manifest.manufacturing_processes = list(inferred.processes)
        else:
            manifest.manufacturing_processes = self.merge_processes(
                existing, inferred.processes
            )
        inferred.applied = True
        return inferred

    def merge_processes(
        self, existing: Sequence[str], inferred: Sequence[str]
    ) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()
        for name in list(existing) + list(inferred):
            if not name or not isinstance(name, str):
                continue
            canonical = taxonomy.normalize(name.strip())
            if canonical is not None:
                display, key = taxonomy.get_display_name(canonical), canonical
            else:
                display, key = name.strip(), name.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(display)
        return out

    def _merge_results(
        self, *results: ProcessInferenceResult
    ) -> ProcessInferenceResult:
        seen_ids: Dict[str, List[str]] = {}
        best_conf = 0.0
        for result in results:
            if not result.evidence:
                continue
            best_conf = max(best_conf, result.confidence)
            for process_id, evidence_list in result.evidence.items():
                bucket = seen_ids.setdefault(process_id, [])
                for item in evidence_list:
                    if item not in bucket:
                        bucket.append(item)
        if not seen_ids:
            return ProcessInferenceResult()
        return self._result_from_ids(seen_ids, best_conf)

    def _result_from_ids(
        self, seen_ids: Dict[str, List[str]], confidence: float
    ) -> ProcessInferenceResult:
        processes: List[str] = []
        for process_id in seen_ids:
            display = taxonomy.get_display_name(process_id)
            if display and display not in processes:
                processes.append(display)
        return ProcessInferenceResult(
            processes=processes,
            evidence=dict(seen_ids),
            confidence=confidence if processes else 0.0,
        )

    @staticmethod
    def _exact_taxonomy_alias(token: str) -> Optional[str]:
        key = taxonomy._normalize_key(token)
        if not key:
            return None
        if key in taxonomy._definitions:
            return key
        if key in taxonomy._alias_map:
            return taxonomy._alias_map[key]
        return taxonomy._tsdc_map.get(token.strip().upper())

    @staticmethod
    def _extension_of(path: str) -> str:
        cleaned = path.split("?", 1)[0].split("#", 1)[0]
        name = PurePosixPath(cleaned.replace("\\", "/")).name
        if not name or "." not in name:
            return ""
        lower = name.lower()
        return lower[lower.rfind(".") :]

    @staticmethod
    def _paths_from_manifest(manifest: object) -> List[str]:
        paths: List[str] = []
        for attr in (
            "manufacturing_files",
            "design_files",
            "making_instructions",
            "technical_specifications",
        ):
            for ref in getattr(manifest, attr, None) or []:
                path = getattr(ref, "path", None) or (
                    ref.get("path") if isinstance(ref, dict) else None
                )
                title = getattr(ref, "title", None) or (
                    ref.get("title") if isinstance(ref, dict) else None
                )
                if path:
                    paths.append(str(path))
                if title:
                    paths.append(str(title))
        return paths
